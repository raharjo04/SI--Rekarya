import pandas as pd
import streamlit as st

from core.artifacts import load_artifacts
from core.charts import cluster_map
from core.config import FEATURES
from core.data import load_dataset
from core.predictor import predict_one
from core.recommender import recommend
from core.ui_theme import (
    empty_state,
    inject_custom_css,
    page_header,
    persona_badge,
    recommendation_card,
    risk_badge,
)


inject_custom_css()

try:
    with st.spinner("Menyiapkan model dan data karyawan..."):
        artifacts = load_artifacts()
        dataset = load_dataset()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()
except ValueError as error:
    st.error(f"Artefak atau dataset tidak valid: {error}")
    st.stop()

page_header(
    "Deteksi Karyawan",
    "Analisis persona, risiko turnover, dan rekomendasi tindak lanjut HR.",
    "🎯",
)

input_column, result_column = st.columns([2, 3], gap="large")
with input_column:
    st.markdown("### Input Parameter Karyawan")
    st.caption("Isi indikator kerja dan karier untuk menjalankan analisis.")
    with st.form(key="prediction_form"):
        st.markdown("#### Kepuasan & evaluasi")
        satisfaction = st.slider(
            "Tingkat kepuasan", 0.0, 1.0, 0.50, 0.01
        )
        evaluation = st.slider(
            "Evaluasi terakhir", 0.0, 1.0, 0.70, 0.01
        )

        st.markdown("#### Beban kerja")
        projects = st.slider("Jumlah proyek", 2, 7, 4)
        hours = st.slider("Jam kerja bulanan", 96, 310, 160)

        st.markdown("#### Masa kerja & karier")
        tenure = st.slider("Masa kerja (tahun)", 2, 10, 3)
        promoted = st.checkbox("Promosi dalam 5 tahun terakhir")
        submitted = st.form_submit_button(
            "Jalankan Analisis Karyawan",
            type="primary",
            width="stretch",
        )

if submitted:
    input_data = {
        "satisfaction_level": satisfaction,
        "last_evaluation": evaluation,
        "number_project": projects,
        "average_montly_hours": hours,
        "time_spend_company": tenure,
        "promotion_last_5years": promoted,
    }
    try:
        result = predict_one(input_data, artifacts)
    except ValueError as error:
        st.error(f"Input tidak dapat dianalisis: {error}")
        st.stop()
    profile_by_cluster = {
        int(item["cluster"]): item for item in artifacts["profiles"]["clusters"]
    }
    profile = profile_by_cluster[result["cluster"]]
    result["profile"] = profile
    result["input_data"] = input_data
    st.session_state["last_employee_analysis"] = result

result = st.session_state.get("last_employee_analysis")
with result_column:
    if result is None:
        empty_state(
            "Analisis karyawan belum dijalankan",
            "Atur parameter di sisi kiri, lalu pilih Jalankan Analisis Karyawan. "
            "Persona dan rekomendasi akan tampil di area ini.",
            "🧭",
        )
    else:
        profile = result["profile"]
        recommendation = recommend(
            profile["persona"],
            result["input_data"],
            risk_level=profile["risk_level"],
        )

        with st.container(border=True):
            st.markdown("### Hasil analisis")
            persona_badge(profile["persona"], profile["badge_color"])
            st.markdown(f"**Klaster {int(result['cluster'])}**")
            risk_badge(profile["risk_level"])

            metric_columns = st.columns(3)
            metric_columns[0].metric(
                "Jarak ke centroid",
                f"{float(result['distance']):.3f}",
                help="Jarak dalam ruang fitur yang telah diskalakan.",
            )
            metric_columns[1].metric(
                "Turnover historis",
                f"{float(profile['turnover_rate']):.1%}",
            )
            metric_columns[2].metric(
                "Skor kepuasan",
                f"{float(result['features']['satisfaction_level']):.2f}",
            )

        for warning in result["warnings"]:
            st.warning(warning)

        background_missing = [
            feature for feature in FEATURES if feature not in dataset.columns
        ]
        if background_missing:
            st.error(f"Kolom dataset tidak tersedia: {', '.join(background_missing)}.")
            st.stop()

        sample = dataset.sample(n=min(5000, len(dataset)), random_state=42)
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
            st.markdown("### Posisi pada peta PCA")
            st.caption(
                "Titik berwarna menunjukkan persona; bintang menandai karyawan yang dianalisis."
            )
            st.plotly_chart(
                cluster_map(
                    points,
                    artifacts["profiles"]["clusters"],
                    artifacts["pca"],
                    artifacts["kmeans"],
                    added_point=result,
                ),
                width="stretch",
                key="employee_cluster_map",
            )

        with st.container(border=True):
            st.markdown("### Rekomendasi HR")
            strategies = list(profile.get("strategy", []))
            if strategies:
                st.markdown("**Strategi untuk persona ini**")
                for index, item in enumerate(strategies, start=1):
                    recommendation_card(item, index)

            rule_recommendations = recommendation["recommendations"]
            if rule_recommendations:
                st.markdown("**Tindak lanjut berdasarkan aturan**")
                for index, item in enumerate(rule_recommendations):
                    rule = (
                        recommendation["triggered_rules"][index]
                        if index < len(recommendation["triggered_rules"])
                        else None
                    )
                    recommendation_card(item, len(strategies) + index + 1, rule)
            elif not strategies:
                st.info("Tidak ada rekomendasi khusus untuk kondisi ini.")

            if recommendation["triggered_rules"]:
                st.caption(
                    "Aturan terpicu: "
                    + ", ".join(recommendation["triggered_rules"])
                    + "."
                )
            st.caption(recommendation["policy_note"])
