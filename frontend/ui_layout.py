import streamlit as st

def set_custom_css():
    st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #d4f5d3 0%, #b7e6c2 100%);
        color: #2b2b2b;
        font-family: 'Segoe UI', sans-serif;
    }
    .stApp {
        background-image: url('https://images.unsplash.com/photo-1501004318641-b39e6451bec6');
        background-size: cover;
        background-position: center;
    }
    .block-container {
        padding: 2rem;
        background-color: rgba(255, 255, 255, 0.85);
        border-radius: 15px;
    }
    .css-1cpxqw2 {
        color: #2e7d32 !important;
    }
    </style>
    """, unsafe_allow_html=True)
