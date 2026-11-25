import pandas as pd
import streamlit as st

from core.artifacts import load_artifacts
from core.charts import cluster_map, evaluation_charts
from core.config import FEATURES
from core.data import load_dataset
from core.ui_theme import (
    PERSONA_COLORS,
    inject_custom_css,
    metric_card,
    page_header,
    persona_badge,
    risk_badge,
)


def _format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


inject_custom_css()

try:
    with st.spinner("Memuat model, profil, dan dataset..."):
        artifacts = load_artifacts()
        dataset = load_dataset()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()
except ValueError as error:
    st.error(f"Artefak atau dataset tidak valid: {error}")
    st.stop()

page_header(
    "Peta Persona Karyawan",
    "Kenali empat kelompok karyawan dan pola kemiripan karakteristik mereka.",
)

profiles = artifacts["profiles"]["clusters"]
optimal_k = int(artifacts["profiles"]["optimal_k"])
evaluation = pd.DataFrame(artifacts["profiles"]["evaluation"])
missing_features = [feature for feature in FEATURES if feature not in dataset.columns]
if missing_features:
    st.error(f"Kolom dataset tidak tersedia: {', '.join(missing_features)}.")
    st.stop()

tab_personas, tab_map, tab_technical = st.tabs(
    ["Persona karyawan", "Peta kemiripan karyawan", "Detail teknis"]
)

with tab_personas:
    card_columns = st.columns(2, gap="large")
    for index, profile in enumerate(profiles):
        means = profile["means"]
        satisfaction = float(means["satisfaction_level"])
        if satisfaction < 0.35:
            satisfaction_text = "kepuasan cenderung rendah"
        elif satisfaction < 0.65:
            satisfaction_text = "kepuasan berada di tingkat menengah"
        else:
            satisfaction_text = "kepuasan cenderung tinggi"
        description = (
            f"Karyawan dalam kelompok ini memiliki {satisfaction_text}, "
            f"bekerja rata-rata {_format_number(means['average_montly_hours'])} jam "
            f"per bulan, dan menangani sekitar "
            f"{_format_number(means['number_project'], 1)} proyek."
        )
        with card_columns[index % 2]:
            with st.container(border=True):
                persona_badge(
                    profile["persona"],
                    PERSONA_COLORS.get(profile["persona"], profile["badge_color"]),
                )
                risk_badge(profile["risk_level"])
                st.markdown("")
                metrics = st.columns(3)
                metrics[0].metric(
                    "Karyawan",
                    _format_number(profile["count"]),
                )
                metrics[1].metric(
                    "Bagian dari tim",
                    _format_number(profile["percentage"], 1) + "%",
                )
                metrics[2].metric(
                    "Pernah keluar",
                    _format_number(profile["turnover_rate"] * 100, 1) + "%",
                )
                st.markdown(description)
                with st.expander("Rekomendasi HR untuk persona ini"):
                    for strategy in profile["strategy"]:
                        st.markdown(f"- {strategy}")

with tab_map:
    sample = dataset.sample(n=min(2000, len(dataset)), random_state=42)
    with st.spinner("Membentuk peta kemiripan karyawan..."):
        scaled = artifacts["scaler"].transform(sample[FEATURES])
        coordinates = artifacts["pca"].transform(scaled)
        points = pd.DataFrame(
            {
                "PCA1": coordinates[:, 0],
                "PCA2": coordinates[:, 1],
                "Cluster": artifacts["kmeans"].predict(scaled),
            }
        )

    with st.container(border=True):
        st.markdown("### Kelompok dengan karakteristik serupa terlihat berdekatan")
        st.plotly_chart(
            cluster_map(
                points,
                profiles,
                artifacts["pca"],
                artifacts["kmeans"],
            ),
            width="stretch",
            key="cluster_map",
        )
        st.caption(
            f"Peta menampilkan {_format_number(len(points))} dari "
            f"{_format_number(len(dataset))} karyawan."
        )

with tab_technical:
    variance = getattr(artifacts["pca"], "explained_variance_ratio_", [])
    explained_variance = float(sum(variance[:2])) if len(variance) >= 2 else 0.0
    metric_columns = st.columns(2, gap="large")
    with metric_columns[0]:
        metric_card("Jumlah kelompok (K)", f"K = {optimal_k}", "◈")
    with metric_columns[1]:
        metric_card(
            "Varians peta kemiripan",
            _format_number(explained_variance * 100, 1) + "%",
            "∿",
        )
    st.caption(
        "K adalah jumlah kelompok; varians menunjukkan informasi yang tertangkap "
        "pada peta; Silhouette, DBI, dan WCSS membandingkan kekompakan serta "
        "pemisahan kelompok."
    )

    with st.container(border=True):
        st.markdown("### Evaluasi model")
        st.plotly_chart(
            evaluation_charts(evaluation, optimal_k),
            width="stretch",
            key="evaluation_charts",
        )

    evaluation_display = evaluation.rename(
        columns={
            "k": "K",
            "wcss": "WCSS",
            "silhouette": "Silhouette",
            "dbi": "Davies-Bouldin",
            "calinski_harabasz": "Calinski-Harabasz",
        }
    ).copy()
    evaluation_display["Status"] = evaluation_display["K"].map(
        lambda value: "Jumlah terpilih" if int(value) == optimal_k else ""
    )

    def highlight_selected(row: pd.Series) -> list[str]:
        if int(row["K"]) == optimal_k:
            return [
                "background-color: #DBEAFE; color: #1E3A8A; font-weight: 700"
            ] * len(row)
        return [""] * len(row)

    def format_id(value: float, decimals: int) -> str:
        return _format_number(value, decimals)

    styled_evaluation = (
        evaluation_display.style.apply(highlight_selected, axis=1)
        .format(
            {
                "WCSS": lambda value: format_id(value, 2),
                "Silhouette": lambda value: format_id(value, 3),
                "Davies-Bouldin": lambda value: format_id(value, 3),
                "Calinski-Harabasz": lambda value: format_id(value, 2),
            }
        )
        .hide(axis="index")
    )
    with st.container(border=True):
        st.markdown("### Tabel evaluasi lengkap")
        st.dataframe(styled_evaluation, width="stretch")
