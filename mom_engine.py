
import json
from pathlib import Path
import math
import pandas as pd
import numpy as np

def zscore_normalise(series: pd.Series, window_months=12, clip=3.0, z_to_100_sigma=2.0):
    """Return 0-100 scaled series where 50 = baseline.
       Steps: rolling z, apply direction before mapping, clip z, map +/- z_to_100_sigma -> 15..85 (linear), clip 0..100.
    """
    # rolling mean/std
    roll_mean = series.rolling(window_months, min_periods=max(6, window_months//2)).mean()
    roll_std  = series.rolling(window_months, min_periods=max(6, window_months//2)).std(ddof=0)
    z = (series - roll_mean) / roll_std.replace(0, np.nan)
    z = z.clip(lower=-clip, upper=clip)
    # map z to 0-100
    # At z = +z_to_100_sigma -> 85; z = -z_to_100_sigma -> 15
    mapped = 50.0 + (z / z_to_100_sigma) * 35.0
    mapped = mapped.clip(lower=0, upper=100)
    return mapped

def transform_series(series: pd.Series, transform: str):
    s = series.copy()
    if transform == "level":
        return s
    elif transform == "delta":
        return s.diff()
    elif transform == "yoy":
        return (s / s.shift(12) - 1.0) * 100.0
    elif transform == "mom":
        return (s / s.shift(1) - 1.0) * 100.0
    else:
        # default passthrough
        return s

def compute_indicator_score(df, ind_spec):
    """Compute 0-100 score for a single indicator.
       df: DataFrame with index=date (monthly), column 'value' for this series id
    """
    series = df["value"].astype(float)
    # Transform
    s = transform_series(series, ind_spec.get("transform", "level"))
    # Direction (flip sign for lower_is_worse)
    direction = ind_spec.get("direction", "higher_is_worse")
    if direction == "lower_is_worse":
        s = -1.0 * s
    # Normalise
    norm = ind_spec.get("normalise", {})
    if not norm:
        norm = {"method":"zscore","window_months":12,"clip":3,"z_to_100_sigma":2}
    if norm.get("method") == "zscore":
        score = zscore_normalise(s, window_months=norm.get("window_months",12),
                                 clip=norm.get("clip",3.0),
                                 z_to_100_sigma=norm.get("z_to_100_sigma",2.0))
    else:
        # fallback: minmax over 5y window
        w = norm.get("window_months", 60)
        roll_min = s.rolling(w, min_periods=max(6, w//2)).min()
        roll_max = s.rolling(w, min_periods=max(6, w//2)).max()
        mm = (s - roll_min) / (roll_max - roll_min).replace(0, np.nan)
        score = (mm * 100.0).clip(0, 100)
    return score

def ewma(series: pd.Series, span=3):
    return series.ewm(span=span, adjust=False).mean()

def momentum_label(series: pd.Series):
    """Simple momentum: z of last 12m and slope of last 3m"""
    if series.dropna().empty:
        return "Unknown"
    last = series.iloc[-1]
    z = (series - series.rolling(12, min_periods=6).mean()) / series.rolling(12, min_periods=6).std(ddof=0)
    z_last = z.iloc[-1]
    slope = (series.iloc[-1] - series.iloc[-3]) if len(series) >= 3 else 0.0
    if z_last >= 0.5 or slope > 0.5:
        return "Worsening"
    elif z_last <= -0.5 or slope < -0.5:
        return "Easing"
    else:
        return "Stable"

class MoMEngine:
    def __init__(self, config: dict):
        self.cfg = config
        # Build fast lookup of indicators per section
        self.sections = self.cfg["sections"]
        self.ind_ids = set()
        for sec in self.sections:
            for ind in sec["indicators"]:
                self.ind_ids.add(ind["id"])

    def compute(self, timeseries: pd.DataFrame):
        """timeseries columns: series_id, date, value"""
        # Pivot by series_id -> column per series
        ts = timeseries.copy()
        ts["date"] = pd.to_datetime(ts["date"])
        ts = ts.sort_values("date")
        # Ensure monthly frequency (fill missing months with NaN)
        full_months = pd.date_range(ts["date"].min(), ts["date"].max(), freq="MS")
        # Holder for scores
        section_scores = {}
        indicator_scores = {}
        headline_weights = []
        headline_series_list = []

        for sec in self.sections:
            sec_id = sec["id"]
            inds = sec["indicators"]
            # Compute indicator scores for this section
            sec_scores = []
            sec_weights = []
            for ind in inds:
                sid = ind["id"]
                # Extract series df for indicator
                sdf = ts[ts["series_id"] == sid][["date","value"]].set_index("date").reindex(full_months)
                if sdf["value"].isna().all():
                    continue  # no data at all
                score = compute_indicator_score(sdf, ind)
                indicator_scores[(sec_id, sid)] = score
                sec_scores.append(score)
                sec_weights.append(ind.get("section_weight", 1.0/len(inds)))
            if not sec_scores:
                continue
            # Weighted mean per month
            W = np.array(sec_weights, dtype=float)
            W = W / W.sum() if W.sum() > 0 else np.ones_like(W)/len(W)
            sec_matrix = np.column_stack([s.values for s in sec_scores])
            sec_df = pd.DataFrame(sec_matrix, index=full_months, columns=[i["id"] for i in inds[:len(sec_scores)]])
            # Recompute weights for available indicators per row (ignore missing via nanmean with weights)
            # We'll compute weighted average handling NaNs
            def weighted_mean_row(vals, weights):
                mask = ~np.isnan(vals)
                if not mask.any():
                    return np.nan
                w = weights[mask]
                v = vals[mask]
                if w.sum() == 0:
                    w = np.ones_like(v)/len(v)
                else:
                    w = w / w.sum()
                return np.average(v, weights=w)

            sec_score_series = pd.Series(
                [weighted_mean_row(sec_df.iloc[i].values.astype(float), W) for i in range(len(sec_df))],
                index=sec_df.index, name=sec_id
            )
            section_scores[sec_id] = sec_score_series

        # Headline MoM
        # Align sections
        if not section_scores:
            raise ValueError("No section scores computed (no data matched config indicator ids).")
        all_idx = full_months
        aligned = pd.concat(section_scores.values(), axis=1).reindex(all_idx)
        # Apply headline weights
        hw = np.array([sec["weight"] for sec in self.sections if sec["id"] in aligned.columns], dtype=float)
        cols = [sec["id"] for sec in self.sections if sec["id"] in aligned.columns]
        # normalise
        hw = hw / hw.sum() if hw.sum() > 0 else np.ones_like(hw)/len(hw)

        def wmean_row(vals, weights):
            mask = ~np.isnan(vals)
            if not mask.any():
                return np.nan
            w = weights[mask]
            v = vals[mask]
            if w.sum() == 0:
                w = np.ones_like(v)/len(v)
            else:
                w = w / w.sum()
            return np.average(v, weights=w)

        headline = pd.Series(
            [wmean_row(aligned.iloc[i].values.astype(float), hw) for i in range(len(aligned))],
            index=aligned.index, name="MoM"
        )
        # Smoothing (EWMA 3m) for display
        headline_smoothed = headline.ewm(span=self.cfg.get("composite",{}).get("smoothing",{}).get("span_months",3),
                                         adjust=False).mean()
        return aligned, headline, headline_smoothed

def load_config(path):
    with open(path, "r") as f:
        return json.load(f)
