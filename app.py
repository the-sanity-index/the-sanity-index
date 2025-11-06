import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from PIL import Image

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
        st.image(labyrinth_logo, use_column_width=True)
    with col2:
        st.markdown(
            "<h1 style='text-align:center;color:silver;'>THE SANITY INDEX</h1>"
            "<p style='text-align:center;color:gray;'>Cutting Through the Chaos</p>",
            unsafe_allow_html=True
        )
    with col3:
        st.image(sanity_logo, use_column_width=True)
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
# Load Data
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
    title="Overall System Stress (0–100)",
    xaxis_title="Date", yaxis_title="Score",
    yaxis=dict(range=[0, 100])
)
st.plotly_chart(fig1, use_container_width=True)

csv_mom = mom_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Headline Data",
    data=csv_mom,
    file_name="mom_scores.csv",
    mime="text/csv"
)

# -------------------------------------------------------------------------
# Section Selector + Chart
# -------------------------------------------------------------------------
section_cols = [col for col in section_df.columns if col != "date"]
st.subheader("Section Scores")
selected = st.selectbox("Choose a section to view:", section_cols)

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
    title=f"{selected.replace('_', ' ').title()} (0–100)",
    xaxis_title="Date", yaxis_title="Score",
    yaxis=dict(range=[0, 100])
)
st.plotly_chart(fig2, use_container_width=True)

csv_section = section_df[["date", selected]].to_csv(index=False).encode("utf-8")
st.download_button(
    f"Download {selected} Data",
    data=csv_section,
    file_name=f"section_{selected}.csv",
    mime="text/csv"
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
