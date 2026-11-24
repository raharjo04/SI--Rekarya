import pandas as pd
import streamlit as st

from core.artifacts import load_artifacts
from core.charts import cluster_map, evaluation_charts
from core.config import FEATURE_LABELS, FEATURES
from core.data import load_dataset
from core.ui_theme import (
    inject_custom_css,
    metric_card,
    page_header,
    persona_badge,
    risk_badge,
)


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
    "Peta Klaster",
    "Jelajahi posisi PCA, kualitas model, dan strategi retensi untuk setiap persona.",
    "🗺️",
)

profiles = artifacts["profiles"]["clusters"]
optimal_k = int(artifacts["profiles"]["optimal_k"])
evaluation = pd.DataFrame(artifacts["profiles"]["evaluation"])
missing_features = [feature for feature in FEATURES if feature not in dataset.columns]
if missing_features:
    st.error(f"Kolom dataset tidak tersedia: {', '.join(missing_features)}.")
    st.stop()

tab_pca, tab_evaluation, tab_profiles = st.tabs(
    [
        "Visualisasi Klaster PCA 2D",
        "Evaluasi Model (K=2–8)",
        "Profil & Strategi Klaster",
    ]
)

with tab_pca:
    variance = getattr(artifacts["pca"], "explained_variance_ratio_", [])
    explained_variance = float(sum(variance[:2])) if len(variance) >= 2 else 0.0
    first, second = st.columns(2, gap="large")
    with first:
        metric_card("Jumlah klaster terpilih", f"K = {optimal_k}", "◈")
    with second:
        metric_card("Varians PCA (PC1 + PC2)", f"{explained_variance:.1%}", "∿")

    sample = dataset.sample(n=min(5000, len(dataset)), random_state=42)
    with st.spinner("Membentuk koordinat PCA..."):
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
        st.markdown("### Sebaran karyawan per persona")
        st.caption(
            "Titik menunjukkan sampel karyawan; simbol berlian menandai centroid tiap klaster."
        )
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
            f"Peta menampilkan {len(points):,} dari {len(dataset):,} karyawan "
            "(sampel tetap, seed 42)."
        )

with tab_evaluation:
    st.markdown("### Evaluasi kualitas klaster")
    st.caption(
        "K terpilih ditandai pada tabel dan garis putus-putus pada grafik evaluasi."
    )
    with st.container(border=True):
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
        lambda value: "K terpilih" if int(value) == optimal_k else ""
    )

    def highlight_selected(row: pd.Series) -> list[str]:
        if int(row["K"]) == optimal_k:
            return [
                "background-color: #DBEAFE; color: #1E3A8A; font-weight: 700"
            ] * len(row)
        return [""] * len(row)

    styled_evaluation = (
        evaluation_display.style.apply(highlight_selected, axis=1)
        .format(
            {
                "WCSS": "{:,.2f}",
                "Silhouette": "{:.3f}",
                "Davies-Bouldin": "{:.3f}",
                "Calinski-Harabasz": "{:,.2f}",
            }
        )
        .hide(axis="index")
    )
    with st.container(border=True):
        st.markdown("### Tabel evaluasi lengkap")
        st.dataframe(styled_evaluation, width="stretch")

with tab_profiles:
    st.markdown("### Persona dan strategi retensi")
    st.caption(
        "Nama persona, tingkat risiko, warna, dan strategi dibaca dari profil klaster."
    )
    persona_order = {
        "High Burnout": 0,
        "Disengaged": 1,
        "Senior Veteran": 2,
        "Engaged Stars": 3,
    }
    profiles_for_display = sorted(
        profiles,
        key=lambda profile: (
            persona_order.get(profile["persona"], len(persona_order)),
            int(profile["cluster"]),
        ),
    )
    card_columns = st.columns(2, gap="large")
    for index, profile in enumerate(profiles_for_display):
        with card_columns[index % 2]:
            with st.container(border=True):
                persona_badge(profile["persona"], profile["badge_color"])
                st.markdown(f"#### Klaster {int(profile['cluster'])}")
                risk_badge(profile["risk_level"])

                metrics = st.columns(3)
                metrics[0].metric(
                    "Karyawan",
                    f"{int(profile['count']):,}".replace(",", "."),
                )
                metrics[1].metric(
                    "Proporsi",
                    f"{float(profile['percentage']):.1f}%",
                )
                metrics[2].metric(
                    "Turnover",
                    f"{float(profile['turnover_rate']):.1%}",
                )

                st.markdown("**Rata-rata fitur karyawan**")
                feature_columns = st.columns(2)
                for feature_index, feature in enumerate(FEATURES):
                    feature_columns[feature_index % 2].metric(
                        FEATURE_LABELS.get(feature, feature),
                        f"{float(profile['means'][feature]):.2f}",
                    )

                with st.expander("Rekomendasi Strategi HR"):
                    for strategy in profile["strategy"]:
                        st.markdown(f"- {strategy}")

    with st.expander("Lihat tabel profil lengkap"):
        profile_rows = []
        for profile in profiles:
            row = {
                "Klaster": int(profile["cluster"]),
                "Persona": profile["persona"],
                "Risiko": profile["risk_level"],
                "Karyawan": int(profile["count"]),
                "Proporsi (%)": float(profile["percentage"]),
                "Turnover (%)": float(profile["turnover_rate"]) * 100,
                "Warna": profile["badge_color"],
            }
            row.update(
                {
                    FEATURE_LABELS.get(feature, feature): profile["means"][feature]
                    for feature in FEATURES
                }
            )
            profile_rows.append(row)
        st.dataframe(
            pd.DataFrame(profile_rows).style.format(
                {
                    "Proporsi (%)": "{:.1f}",
                    "Turnover (%)": "{:.1f}",
                    **{
                        FEATURE_LABELS.get(feature, feature): "{:.2f}"
                        for feature in FEATURES
                    },
                }
            ),
            hide_index=True,
            width="stretch",
        )
