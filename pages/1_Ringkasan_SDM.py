import streamlit as st

from core.charts import project_turnover, summary_scatter
from core.data import load_dataset, summary_stats
from core.ui_theme import inject_custom_css, metric_card, page_header


def _format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


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
    "Ringkasan SDM",
    "Gambaran tenaga kerja, pola beban kerja, dan risiko karyawan keluar.",
)

first, second, third, fourth = st.columns(4)
with first:
    metric_card(
        "Total karyawan",
        _format_number(stats["total_karyawan"]),
        "👥",
    )
with second:
    metric_card(
        "Karyawan keluar",
        _format_number(stats["turnover_rate"] * 100, 1) + "%",
        "↗️",
    )
with third:
    metric_card(
        "Rata-rata kepuasan",
        _format_number(stats["rata_kepuasan"], 2),
        "💠",
    )
with fourth:
    metric_card(
        "Jam kerja rata-rata",
        _format_number(stats["rata_jam_bulanan"], 0) + " jam",
        "⏱️",
    )

project_summary = stats["project_summary"]
highest_turnover = project_summary.loc[project_summary["turnover_rate"].idxmax()]
largest_group = project_summary.loc[project_summary["jumlah_karyawan"].idxmax()]
high_load = data.loc[
    (data["average_montly_hours"] > 250) & (data["satisfaction_level"] < 0.4)
]
insights = [
    (
        f"Turnover tertinggi ada pada karyawan dengan "
        f"{int(highest_turnover['jumlah_proyek'])} proyek "
        f"({_format_number(highest_turnover['turnover_rate'] * 100, 1)}%; "
        f"n={_format_number(highest_turnover['jumlah_karyawan'])})."
    ),
    (
        f"Kelompok terbesar adalah karyawan dengan "
        f"{int(largest_group['jumlah_proyek'])} proyek "
        f"(n={_format_number(largest_group['jumlah_karyawan'])})."
    ),
]
if not high_load.empty:
    high_load_turnover = float(high_load["left"].mean())
    insights.append(
        f"{_format_number(len(high_load))} karyawan memiliki jam kerja di atas "
        f"250 jam dan kepuasan di bawah 0,40; "
        f"{_format_number(high_load_turnover * 100, 1)}% di antaranya keluar."
    )

with st.container(border=True):
    st.markdown("### Temuan utama")
    for insight in insights[:3]:
        st.markdown(f"- {insight}")

left, right = st.columns(2, gap="large")
with left:
    with st.container(border=True):
        st.markdown("### Beban tinggi dan kepuasan rendah perlu diperhatikan")
        st.plotly_chart(
            summary_scatter(stats["scatter_sample"]),
            width="stretch",
            key="summary_scatter",
        )
        st.caption("Titik dibatasi agar pola utama tetap terbaca.")
with right:
    with st.container(border=True):
        st.markdown(
            f"### Turnover tertinggi tercatat pada karyawan dengan "
            f"{int(highest_turnover['jumlah_proyek'])} proyek"
        )
        st.plotly_chart(
            project_turnover(project_summary),
            width="stretch",
            key="project_turnover",
        )
