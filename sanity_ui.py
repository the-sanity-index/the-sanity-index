# sanity_ui.py — unified UI helpers for The Sanity Index
# Handles titles, captions, section headers, and dark/light theme styling.

import streamlit as st

# ---------------------------------------------------------------------
# Inject global CSS (padding fix + adaptive body colour)
# ---------------------------------------------------------------------
def sanity_inject_css(theme: str = "dark"):
    """
    Injects base CSS styling (text colour, padding, etc.)
    Call once at the start of app.py.
    """
    body_color = "#111111" if theme == "light" else "#d1d1d1"
    st.markdown(
        f"""
        <style>
        .stApp {{
            color: {body_color};
        }}
        /* Add breathing space so logos aren't cut off */
        .block-container {{
            padding-top: 3rem;
            padding-bottom: 2rem;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------
# Title + Subtitle block
# ---------------------------------------------------------------------
def sanity_title(title: str, subtitle: str | None = None, theme: str = "dark"):
    """
    Renders a consistent title and optional subtitle block.
    """
    if theme == "light":
        title_color = "#202020"
        sub_color = "#555555"
    else:
        title_color = "#d1d1d1"
        sub_color = "#b0b0b0"

    subtitle_html = (
        f"<div style='font-size:15px;color:{sub_color};"
        f"margin-top:-6px;margin-bottom:10px;'>{subtitle}</div>"
        if subtitle else ""
    )

    st.markdown(
        f"""
        <div style='text-align:center;margin-top:10px;margin-bottom:15px;'>
            <div style='font-size:22px;color:{title_color};font-weight:600;'>
                {title}
            </div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------
# Caption block (source/date/status/quote)
# ---------------------------------------------------------------------
def sanity_caption(
    source: str,
    date: str,
    status: str = "Stable",
    quote: str | None = None,
    theme: str = "dark",
):
    """
    Adds a standardised caption under charts.
    """
    color_map = {
        "Normal": "🟢",
        "Warning": "🟠",
        "Elevated": "🟠",
        "Acute": "🔴",
    }
    color_emoji = color_map.get(status, "⚪")

    if theme == "light":
        text_color = "#333333"
        bg_color = "#f8f8f8"
    else:
        text_color = "#bfbfbf"
        bg_color = "transparent"

    quote_html = f"<br><em>\"{quote}\"</em>" if quote else ""

    st.markdown(
        f"""
        <div style='text-align:center;
                    color:{text_color};
                    background-color:{bg_color};
                    font-size:14px;
                    padding:4px;
                    border-radius:4px;'>
            <em>Last updated:</em> {source}, {date}.<br>
            {color_emoji} <em>Sanity Index Read:</em> {status}.{quote_html}
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------
# Section header + divider
# ---------------------------------------------------------------------
def sanity_section(name: str, kicker: str | None = None, theme: str = "dark"):
    """
    Renders a clean module header with an optional kicker (short context line)
    and a subtle divider. Use for each section/module.
    """
    if theme == "light":
        name_color = "#202020"
        kick_color = "#555555"
        rule_color = "#e5e5e5"
    else:
        name_color = "#d1d1d1"
        kick_color = "#a9a9a9"
        rule_color = "#3a3a3a"

    kicker_html = (
        f"<div style='font-size:14px;color:{kick_color};margin-top:-4px;'>{kicker}</div>"
        if kicker
        else ""
    )

    st.markdown(
        f"""
        <div style='margin-top:18px;margin-bottom:10px;'>
            <div style='font-size:20px;color:{name_color};
                        font-weight:600;text-align:center;'>
                {name}
            </div>
            {kicker_html}
            <hr style='border:0;border-top:1px solid {rule_color};
                       margin:8px 0 12px 0;'>
        </div>
        """,
        unsafe_allow_html=True
    )

