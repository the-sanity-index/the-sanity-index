# sanity_ui.py — UI helpers for The Sanity Index (dark/light adaptive)
import streamlit as st

# ---- Title + Subtitle ----------------------------------------------------
def sanity_title(title, subtitle=None, theme="dark"):
    if theme == "light":
        title_color = "#202020"; sub_color = "#555555"
    else:
        title_color = "#d1d1d1"; sub_color = "#b0b0b0"

    subtitle_html = (
        f"<div style='font-size:15px;color:{sub_color};margin-top:-6px;margin-bottom:10px;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style='text-align:center;margin-top:10px;margin-bottom:15px;'>
            <div style='font-size:22px;color:{title_color};font-weight:600;'>{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- Caption (source/date/status/quote) ----------------------------------
def sanity_caption(source, date, status="Stable", quote=None, theme="dark"):
    color_map = {"Normal":"🟢","Warning":"🟠","Elevated":"🟠","Acute":"🔴"}
    color_emoji = color_map.get(status, "⚪")

    if theme == "light":
        text_color = "#333333"; bg_color = "#f8f8f8"
    else:
        text_color = "#bfbfbf"; bg_color = "transparent"

    quote_html = f"<br><em>\"{quote}\"</em>" if quote else ""
    st.markdown(
        f"""
        <div style='text-align:center;color:{text_color};background-color:{bg_color};
                    font-size:14px;padding:4px;border-radius:4px;'>
            <em>Last updated:</em> {source}, {date}.<br>
            {color_emoji} <em>Sanity Index Read:</em> {status}.{quote_html}
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- Section header + divider --------------------------------------------
def sanity_section(name, kicker=None, theme="dark"):
    if theme == "light":
        name_color = "#202020"; kick_color = "#555555"; rule_color = "#e5e5e5"
    else:
        name_color = "#d1d1d1"; kick_color = "#a9a9a9"; rule_color = "#3a3a3a"

    kicker_html = (
        f"<div style='font-size:14px;color:{kick_color};margin-top:-4px;'>{kicker}</div>"
        if kicker else ""
    )
    st.markdown(
        f"""
        <div style='margin-top:18px;margin-bottom:10px;'>
            <div style='font-size:20px;color:{name_color};font-weight:600;text-align:center;'>{name}</div>
            {kicker_html}
            <hr style='border:0;border-top:1px solid {rule_color};margin:8px 0 12px 0;'>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- Optional: small CSS tidy --------------------------------------------
def sanity_inject_css(theme="dark"):
    body_color = "#111111" if theme == "light" else "#d1d1d1"
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 1rem; padding-bottom: 2rem; }}
        .stApp {{ color: {body_color}; }}
        </style>
        """,
        unsafe_allow_html=True
    )
