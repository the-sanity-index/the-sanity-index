# free_feed_api.py — Free Market Feed for The Sanity Index
# Final version: Binance crypto (unlimited), Stooq indices (CSV), Frankfurter FX.

import time
import httpx
import csv
from io import StringIO
from fastapi import FastAPI

API = FastAPI(title="Sanity Free Feed API", version="3.0")

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def now_ts() -> int:
    return int(time.time())


async def fetch_text(url: str):
    """Fetch raw text (used for Stooq CSV endpoints)."""
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


async def fetch_json(url: str, params=None):
    """Fetch JSON for Binance and FX."""
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()


def parse_stooq_csv(raw: str):
    """
    Stooq returns a single CSV row:
    SYMBOL,DATE,TIME,OPEN,HIGH,LOW,CLOSE,VOLUME
    We extract CLOSE.
    """
    f = StringIO(raw)
    reader = csv.reader(f)
    row = next(reader)

    # CLOSE price is index 6
    if len(row) > 6 and row[6] not in ["", "N/A", None]:
        try:
            return float(row[6])
        except:
            return None
    return None

# ---------------------------------------------------------------------
# CRYPTO — Binance (no rate limits)
# ---------------------------------------------------------------------

@API.get("/crypto")
async def crypto():
    urls = {
        "BTC": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "ETH": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
    }

    out = {}
    for sym, url in urls.items():
        try:
            j = await fetch_json(url)
            out[sym] = float(j["price"])
        except Exception as e:
            out[sym] = {"error": str(e)}

    return {"ts": now_ts(), "data": out}

# ---------------------------------------------------------------------
# INDICES — Stooq (no keys, no rate limits)
# ---------------------------------------------------------------------

STOOQ_URL = "https://stooq.com/q/l/?s={symbol}&i=d"

STOOQ_SYMBOLS = {
    "SPX": "^spx",     # S&P 500
    "NDX": "^ndx",     # Nasdaq 100
    "FTSE": "^ftse",   # FTSE 100
    "DAX": "^dax",     # DAX 40
    "N225": "^nkx",    # Nikkei (Stooq uses NKX)
    "HSI": "^hsi",     # Hang Seng
}

@API.get("/indices")
async def indices():
    out = {}

    for name, stoq_symbol in STOOQ_SYMBOLS.items():
        try:
            url = STOOQ_URL.format(symbol=stoq_symbol)
            raw = await fetch_text(url)
            price = parse_stooq_csv(raw)

            if price is not None:
                out[name] = {"last": price}
            else:
                out[name] = {"error": "No data"}
        except Exception as e:
            out[name] = {"error": str(e)}

    return {"ts": now_ts(), "data": out}

# ---------------------------------------------------------------------
# FX — Frankfurter (ECB)
# ---------------------------------------------------------------------

@API.get("/fx")
async def fx():
    try:
        j = await fetch_json("https://api.frankfurter.app/latest", params={"base": "USD"})
        return {"date": j.get("date"), "data": j.get("rates", {})}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@API.get("/health")
async def health():
    return {"ok": True, "ts": now_ts()}
