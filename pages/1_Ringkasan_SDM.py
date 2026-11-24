import streamlit as st

from core.charts import project_turnover, summary_scatter
from core.data import load_dataset, summary_stats
from core.ui_theme import inject_custom_css, metric_card, page_header


inject_custom_css()

try:
    with st.spinner("Menyiapkan ringkasan data SDM..."):
        data = load_dataset()
        stats = summary_stats(data)
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()
except ValueError as error:
    st.error(f"Dataset tidak dapat diringkas: {error}")
    st.stop()

page_header(
    "Ringkasan Eksekutif SDM",
    f"Ikhtisar {stats['total_karyawan']:,} catatan karyawan dan indikator retensi dari dataset HR.",
    "📈",
)

first, second, third, fourth = st.columns(4)
with first:
    metric_card(
        "Total karyawan",
        f"{stats['total_karyawan']:,}".replace(",", "."),
        "👥",
    )
with second:
    metric_card("Turnover rate", f"{stats['turnover_rate']:.1%}", "↗️")
with third:
    metric_card("Rata-rata kepuasan", f"{stats['rata_kepuasan']:.2f}", "💠")
with fourth:
    metric_card("Rata-rata jam kerja", f"{stats['rata_jam_bulanan']:.1f}", "⏱️")

st.markdown("")
left, right = st.columns(2, gap="large")
with left:
    with st.container(border=True):
        st.markdown("### Jam kerja & kepuasan")
        st.caption(
            "Hubungan jam kerja bulanan dengan kepuasan, dibedakan menurut status karyawan."
        )
        st.plotly_chart(
            summary_scatter(stats["scatter_sample"]),
            width="stretch",
            key="summary_scatter",
        )
        st.caption(
            "Scatter memakai sampel acak tetap: maksimal 3.000 titik (seed 42)."
        )
with right:
    with st.container(border=True):
        st.markdown("### Proyek & turnover")
        st.caption(
            "Bandingkan jumlah karyawan dan tingkat turnover pada tiap jumlah proyek."
        )
        st.plotly_chart(
            project_turnover(stats["project_summary"]),
            width="stretch",
            key="project_turnover",
        )

highest_turnover = stats["project_summary"].loc[
    stats["project_summary"]["turnover_rate"].idxmax()
]
st.info(
    f"Insight dataset: turnover keseluruhan {stats['turnover_rate']:.1%}; "
    f"tingkat tertinggi berdasarkan jumlah proyek terlihat pada "
    f"{int(highest_turnover['jumlah_proyek'])} proyek "
    f"({highest_turnover['turnover_rate']:.1%})."
)
