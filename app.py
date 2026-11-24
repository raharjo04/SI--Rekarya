import streamlit as st

from core.ui_theme import inject_custom_css, page_header, sidebar_branding

st.set_page_config(
    page_title="SI-REKARYA",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()
sidebar_branding()

navigation = st.navigation(
    [
        st.Page(
            "pages/1_Ringkasan_SDM.py",
            title="Ringkasan SDM",
            icon="📈",
            default=True,
        ),
        st.Page(
            "pages/2_Peta_Klaster.py",
            title="Peta Klaster",
            icon="🗺️",
        ),
        st.Page(
            "pages/3_Deteksi_Karyawan.py",
            title="Deteksi Karyawan",
            icon="🎯",
        ),
        st.Page(
            "pages/4_Audit_Data_Massal.py",
            title="Audit Data Massal",
            icon="📋",
        ),
    ]
)

page_header(
    "SI-REKARYA",
    "Sistem Inteligensi Retensi & Klasterisasi Karyawan Berbasis K-Means",
    "✦",
)
navigation.run()
