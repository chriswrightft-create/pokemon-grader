import streamlit as st


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
    st.image("assets/quickstart.gif", caption="Quick walkthrough of initial setup.", use_container_width=True)
