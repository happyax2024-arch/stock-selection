"""Custom CSS styles for the Streamlit UI."""
import streamlit as st


def apply_styles():
    st.markdown("""
    <style>
    .stApp {
        max-width: 100%;
    }
    .main-header {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .stDataFrame {
        font-size: 0.85rem;
    }
    section[data-testid="stSidebar"] {
        min-width: 280px;
    }
    </style>
    """, unsafe_allow_html=True)
