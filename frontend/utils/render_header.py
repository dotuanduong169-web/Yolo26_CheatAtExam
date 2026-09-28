import streamlit as st
from utils.load_css import load_css

def render_page_header(title: str):
    """Vẽ thanh header chung: logo ExamCheat AI + tiêu đề trang."""
    st.markdown(load_css("styles/header.css"), unsafe_allow_html=True)

    st.markdown(f"""
    <div class="global-top-bar">
        <div class="top-logo-section">
            <div class="top-logo-box">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 3v18h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M7 14l4-4 4 4 6-6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 8v-4h-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div class="top-logo-text">
                <div class="top-logo-main">ExamCheat AI</div>
                <div class="top-logo-sub">Giám sát gian lận phòng thi</div>
            </div>
        </div>
        <div class="top-page-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
