import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from PIL import Image
import os
import httpx

# --------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------
st.set_page_config(page_title="The Sanity Index", layout="centered")

# --------------------------------------------------------------------
# Load logos safely
# --------------------------------------------------------------------
try:
    sanity_logo = Image.open("sanity_logo.png")
    labyrinth_logo = Image.open("labyrinth_logo.png")
except:
    sanity_logo = labyrinth_logo = None

# --------------------------------------------------------------------
# Header layout
# --------------------------------------------------------------------
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    if labyrinth_logo:
        st.image(labyrinth_logo, width=150)

with col2:
    st.markdown(
        "<h1 style='text-align:center;color:silver;'>THE SANITY INDEX</h1>"
        "<p style='text-align:center;color:gray;'>Cutting Through the Chaos</p>",
        unsafe_allow_html=True
    )

with col3:
    if sanity_logo:
        st.image(sanity_logo, width=150)

st.markdown("<hr>", unsafe_allow_html=True)

# --------------------------------------------------------------------
# Helper for API calls
# --------------------------------------------------------------------
API_BASE = os.getenv("SANITY_API_BASE", "http://localhost:8000")

def fetch_json(path, params=None, default=None):
    try:
        with httpx.Client(timeout=8) as c:
            r = c.get(f"{API_BASE}{path}", params=params)
            r.raise_for_status()
            return r.json()
    except:
        return default or {}

# --------------------------------------------------------------------
# LIVE BOARD
# --------------------------------------------------------------------
st.markdown("### Live Board (Free Feeds)")

quotes = fetch_json("/indices") or {}
crypto = fetch_json("/crypto") or {}

# ---------------------- INDICES ----------------------
if quotes.get("data"):
    q = quotes["data"]

    def safe(sym):
        try:
            return q[sym].get("last", "—")
        except:
            return "—"

    st.markdown(
        f"**SPX** {safe('SPX')}  |  "
        f"**NDX** {safe('NDX')}  |  "
        f"**FTSE** {safe('FTSE')}  |  "
        f"**DAX** {safe('DAX')}"
    )

# ---------------------- CRYPTO ----------------------
if crypto.get("data"):
    c = crypto["data"]

    def csafe(sym):
        try:
            return c[sym]
        except:
            return "—"

    st.markdown(
        f"**BTC** ${csafe('BTC')}  |  "
        f"**ETH** ${csafe('ETH')}"
    )

st.markdown("<hr>", unsafe_allow_html=True)

# --------------------------------------------------------------------
# Load Data (Headline + Section scores)
# --------------------------------------------------------------------

try:
    mom_df = pd.read_csv("mom_scores.csv", parse_dates=["date"])
except:
    st.error("'mom_scores.csv' missing.")
    st.stop()

try:
    section_df = pd.read_csv("section_scores.csv")
    if "Unnamed: 0" in section_df.columns:
        section_df.rename(columns={"Unnamed: 0": "date"}, inplace=True)
    section_df["date"] = pd.to_datetime(section_df["date"])
except:
    st.error("'section_scores.csv' missing.")
    st.stop()

# --------------------------------------------------------------------
# Headline chart
# --------------------------------------------------------------------
st.subheader("Headline Sanity Index")

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
    xaxis_title="Date",
    yaxis_title="Score",
    yaxis=dict(range=[0, 100])
)

st.plotly_chart(fig1, use_container_width=True)

st.download_button(
    "Download Headline Data",
    data=mom_df.to_csv(index=False).encode("utf-8"),
    file_name="mom_scores.csv"
)

# --------------------------------------------------------------------
# Section chart
# --------------------------------------------------------------------
st.subheader("Module Scores")

section_cols = [c for c in section_df.columns if c != "date"]
selected = st.selectbox("Choose a module:", section_cols)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=section_df["date"], y=section_df[selected],
    mode="lines+markers",
    line=dict(color="silver")
))
fig2.add_hline(y=50, line=dict(dash="dash", color="gray"))

fig2.update_layout(
    paper_bgcolor="#141210",
    plot_bgcolor="#141210",
    font=dict(color="silver"),
    xaxis_title="Date",
    yaxis_title="Score",
    yaxis=dict(range=[0, 100]),
    title=f"{selected.replace('_', ' ').title()} (0–100)"
)

st.plotly_chart(fig2, use_container_width=True)

st.download_button(
    f"Download {selected} Data",
    data=section_df[["date", selected]].to_csv(index=False).encode("utf-8"),
    file_name=f"{selected}_data.csv"
)

st.markdown(
    "<hr><p style='text-align:center;color:gray;font-size:12px;'>"
    "Powered by Labyrinth Analytics © 2025"
    "</p>",
    unsafe_allow_html=True
)
