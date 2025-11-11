import os
import httpx
import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from PIL import Image

# UI helpers (from sanity_ui.py)
from sanity_ui import sanity_title, sanity_caption, sanity_section, sanity_inject_css
sanity_inject_css(theme="dark")

# -------------------------------------------------------------------------
# Page setup
# -------------------------------------------------------------------------
st.set_page_config(page_title="The Sanity Index", layout="centered")

# -------------------------------------------------------------------------
# Logos + Header  (safe even if images missing)
# -------------------------------------------------------------------------
try:
    sanity_logo = Image.open("sanity_logo.png")
    labyrinth_logo = Image.open("labyrinth_logo.png")

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.image(labyrinth_logo, use_container_width=True)
    with col2:
        st.markdown(
            "<h1 style='text-align:center;color:silver;'>THE SANITY INDEX</h1>"
            "<p style='text-align:center;color:gray;'>Cutting Through the Chaos</p>",
            unsafe_allow_html=True
        )
    with col3:
        st.image(sanity_logo, use_container_width=True)
except Exception:
    st.markdown(
        """
        <div style="text-align:center;">
            <h1 style="color:silver;">THE SANITY INDEX</h1>
            <p style="color:gray;font-size:18px;">Cutting Through the Chaos</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<hr style='border:1px solid silver;'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Live Board (free feeds via free_feed_api.py)
# -------------------------------------------------------------------------
API_BASE = os.getenv("SANITY_API_BASE", "http://localhost:8000")  # set on Render for production

def fetch_json(path, params=None, default=None):
    try:
        with httpx.Client(timeout=4) as c:
            r = c.get(f"{API_BASE}{path}", params=params)
            r.raise_for_status()
            return r.json()
    except Exception:
        return default

st.markdown("### Live Board (free feeds)")
quotes = fetch_json("/indices") or {}
crypto = fetch_json("/crypto", {"ids": "bitcoin,ethereum"}) or {}

if quotes.get("data"):
    q = quotes["data"]
    st.markdown(
        f"**SPX** {q['^GSPC']['last']}  |  **NDX** {q['^NDX']['last']}  |  "
        f"**FTSE** {q['^FTSE']['last']}  |  **DAX** {q['^GDAXI']['last']}"
    )
if crypto.get("data"):
    c = crypto["data"]
    st.markdown(f"**BTC** ${c['BITCOIN']['USD']}  |  **ETH** ${c['ETHEREUM']['USD']}")

# -------------------------------------------------------------------------
# Load Data (headline + sections)
# -------------------------------------------------------------------------
try:
    mom_df = pd.read_csv("mom_scores.csv", parse_dates=["date"])
except FileNotFoundError:
    st.error("'mom_scores.csv' not found. Place it in the same folder as this script.")
    st.stop()

try:
    section_df = pd.read_csv("section_scores.csv")
    if "Unnamed: 0" in section_df.columns:
        section_df.rename(columns={"Unnamed: 0": "date"}, inplace=True)
    section_df["date"] = pd.to_datetime(section_df["date"])
except FileNotFoundError:
    st.error("'section_scores.csv' not found. Place it in the same folder as this script.")
    st.stop()

# -------------------------------------------------------------------------
# Headline Chart
# -------------------------------------------------------------------------
sanity_title(
    title="Headline Sanity Index",
    subtitle="Overall System Stress (0–100) — 50 = baseline",
    theme="dark"
)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=mom_df["date"], y=mom_df["MoM_raw"],
    mode="lines", name="Raw Index",
    line=dict(dash="dot", color="silver")
))
fig1.add_trace(go.Scatter(
    x=mom_df["date"], y=mom_df["MoM_smoothed"],
    mode="lines", name="Smoothed (3 mo EWMA)",
    line=dict(width=3, color="white")
))
fig1.add_hline(y=50, line=dict(dash="dash", color="gray"))
fig1.update_layout(
    paper_bgcolor="#141210",
    plot_bgcolor="#141210",
    font=dict(color="silver"),
    xaxis_title="Date", yaxis_title="Score",
    yaxis=dict(range=[0, 100]),
    showlegend=True
)
st.plotly_chart(fig1, use_container_width=True)

csv_mom = mom_df.to_csv(index=False).encode("utf-8")
st.download_button("Download Headline Data", data=csv_mom, file_name="mom_scores.csv", mime="text/csv")

sanity_caption(
    source="Labyrinth Analytics — MoM engine",
    date=mom_df['date'].max().strftime("%d %b %Y"),
    status="Stable",
    quote="Reality, without the garnish.",
    theme="dark"
)

# -------------------------------------------------------------------------
# Section Selector + Chart
# -------------------------------------------------------------------------
sanity_section(
    name="Module Scores",
    kicker="Select a module to view its 10-year score history (0–100).",
    theme="dark"
)

section_cols = [col for col in section_df.columns if col != "date"]
selected = st.selectbox("Choose a module:", section_cols, index=0)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=section_df["date"], y=section_df[selected],
    mode="lines+markers", name=selected,
    line=dict(color="silver")
))
fig2.add_hline(y=50, line=dict(dash="dash", color="gray"))
fig2.update_layout(
    paper_bgcolor="#141210",
    plot_bgcolor="#141210",
    font=dict(color="silver"),
    xaxis_title="Date", yaxis_title="Score",
    yaxis=dict(range=[0, 100]),
    title=f"{selected.replace('_', ' ').title()} (0–100)"
)
st.plotly_chart(fig2, use_container_width=True)

csv_section = section_df[["date", selected]].to_csv(index=False).encode("utf-8")
st.download_button(f"Download {selected} Data", data=csv_section, file_name=f"section_{selected}.csv", mime="text/csv")

sanity_caption(
    source="Labyrinth Analytics — MoM engine",
    date=section_df['date'].max().strftime("%d %b %Y"),
    status="Stable",
    quote="We measure what matters, not what trends.",
    theme="dark"
)

# -------------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------------
st.markdown(
    "<hr><p style='text-align:center;color:gray;font-size:12px;'>"
    "Powered by Labyrinth Analytics © 2025"
    "</p>",
    unsafe_allow_html=True
)
