from pathlib import Path

import streamlit as st

_QUICKSTART_GIF = Path(__file__).resolve().parent / "assets" / "quickstart.gif"


def apply_page_chrome() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {display: none !important;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        div[data-testid="collapsedControl"] {display: none !important;}
        .block-container {padding-top: 2rem !important;}
        h1 {margin-top: 0 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 3.25rem; padding-bottom: 0.4rem;}
        h1 {margin-top: 0; margin-bottom: 0.2rem; font-size: 2rem;}
        p {margin-bottom: 0.5rem;}
        div[data-testid="stNumberInput"] {margin-bottom: 0.25rem;}
        div[data-testid="stMetricValue"] {font-size: 2rem;}
        div[data-testid="stImage"] img {max-height: 70vh; width: auto; object-fit: contain;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_quickstart() -> None:
    st.subheader("How to use")
    st.image(str(_QUICKSTART_GIF), caption="Quick walkthrough of initial setup.", width="stretch")
