import pandas as pd
import streamlit as st

from core.artifacts import load_artifacts
from core.charts import cluster_map, employee_group_comparison
from core.config import FEATURES
from core.data import load_dataset
from core.predictor import predict_one
from core.recommender import recommend
from core.ui_theme import (
    PERSONA_COLORS,
    empty_state,
    inject_custom_css,
    page_header,
    persona_badge,
    recommendation_card,
    risk_badge,
)


def _format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


inject_custom_css()

st.markdown(
    """
    <style>
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primary"] p,
    button[data-testid="stBaseButton-primary"] span,
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stFormSubmitButton"] button p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    "Bandingkan karakteristik karyawan dengan kelompok yang paling serupa.",
)

with st.container(border=True):
    st.markdown("### Masukkan karakteristik karyawan")
    st.caption("Isi indikator kerja dan karier, lalu jalankan analisis.")
    with st.form(key="prediction_form"):
        first, second, third = st.columns(3, gap="large")
        with first:
            satisfaction = st.slider(
                "Tingkat kepuasan", 0.0, 1.0, 0.50, 0.01
            )
            evaluation = st.slider(
                "Evaluasi terakhir", 0.0, 1.0, 0.70, 0.01
            )
        with second:
            projects = st.slider("Jumlah proyek", 2, 7, 4)
            hours = st.slider("Jam kerja bulanan", 96, 310, 160)
        with third:
            tenure = st.slider("Masa kerja (tahun)", 2, 10, 3)
            promoted = st.checkbox("Promosi dalam 5 tahun terakhir")
        submitted = st.form_submit_button(
            "Jalankan analisis",
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
if result is None:
    empty_state(
        "Analisis karyawan belum dijalankan",
        "Atur parameter di atas, lalu pilih Jalankan analisis untuk melihat persona "
        "dan rekomendasi.",
        "🧭",
    )
    st.stop()

profile = result["profile"]
recommendation = recommend(
    profile["persona"],
    result["input_data"],
    risk_level=profile["risk_level"],
)

with st.container(border=True):
    st.markdown("### Hasil analisis")
    persona_badge(
        profile["persona"],
        PERSONA_COLORS.get(profile["persona"], profile["badge_color"]),
    )
    risk_badge(profile["risk_level"])
    historical_exits = round(float(profile["turnover_rate"]) * 100)
    st.markdown(
        f"### Dari 100 karyawan serupa, sekitar {historical_exits} pernah keluar."
    )

for warning in result["warnings"]:
    st.warning(warning)

with st.container(border=True):
    st.markdown("### Rekomendasi HR — prioritas tindak lanjut")
    prioritized = list(recommendation["recommendations"])
    prioritized.extend(
        item
        for item in profile.get("strategy", [])
        if item not in prioritized
    )
    if prioritized:
        for index, item in enumerate(prioritized, start=1):
            recommendation_card(item, index)
    else:
        st.info("Tidak ada rekomendasi khusus untuk kondisi ini.")
    st.caption(recommendation["policy_note"])

if recommendation["triggered_rules"]:
    st.caption(
        "Tindak lanjut diprioritaskan berdasarkan indikator yang perlu perhatian."
    )

with st.container(border=True):
    st.markdown("### Perbandingan dengan rata-rata kelompok")
    st.caption(
        "Setiap baris membandingkan nilai karyawan dengan rata-rata persona "
        "(rata-rata kelompok = 100)."
    )
    st.plotly_chart(
        employee_group_comparison(
            result["features"],
            profile["means"],
        ),
        width="stretch",
        key="employee_group_comparison",
    )

with st.expander("Detail teknis"):
    st.markdown(
        f"**Jarak ke pusat kelompok:** {_format_number(result['distance'], 3)}. "
        "Jarak yang lebih kecil berarti karakteristik lebih dekat dengan "
        "kelompok yang dipilih."
    )
    st.markdown(
        f"**Skor kepuasan input:** "
        f"{_format_number(result['features']['satisfaction_level'], 2)} "
        "pada skala 0–1."
    )

background_missing = [feature for feature in FEATURES if feature not in dataset.columns]
if background_missing:
    st.error(f"Kolom dataset tidak tersedia: {', '.join(background_missing)}.")
    st.stop()

sample = dataset.sample(n=min(2000, len(dataset)), random_state=42)
scaled = artifacts["scaler"].transform(sample[FEATURES])
coordinates = artifacts["pca"].transform(scaled)
points = pd.DataFrame(
    {
        "PCA1": coordinates[:, 0],
        "PCA2": coordinates[:, 1],
        "Cluster": artifacts["kmeans"].predict(scaled),
    }
)
with st.expander("Lihat posisi karyawan pada peta kemiripan"):
    st.caption("Bintang berbingkai putih menandai karyawan yang sedang dianalisis.")
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