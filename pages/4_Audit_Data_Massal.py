from io import BytesIO

import pandas as pd
import streamlit as st

from core.artifacts import load_artifacts
from core.charts import cluster_distribution
from core.config import BATCH_MAX_BYTES, BATCH_MAX_ROWS
from core.predictor import predict_batch
from core.recommender import recommend
from core.ui_theme import inject_custom_css, page_header


inject_custom_css()

template = pd.DataFrame(
    columns=[
        "satisfaction_level",
        "last_evaluation",
        "number_project",
        "average_montly_hours",
        "time_spend_company",
    ]
)

header_column, download_column = st.columns([3, 1], gap="large")
with header_column:
    page_header(
        "Audit Data Massal",
        "Validasi dan prediksi persona karyawan dari satu file CSV.",
        "📋",
    )
with download_column:
    st.markdown("")
    st.markdown("")
    st.download_button(
        "⬇️  Unduh template CSV",
        data=template.to_csv(index=False).encode("utf-8"),
        file_name="template_audit_karyawan.csv",
        mime="text/csv",
        width="stretch",
    )

step_columns = st.columns(3, gap="medium")
for step_column, number, title in zip(
    step_columns,
    ("1", "2", "3"),
    ("Unduh template", "Unggah CSV", "Tinjau hasil"),
):
    with step_column:
        st.markdown(
            f'<div class="si-step"><span class="si-step-number">{number}</span>'
            f"{title}</div>",
            unsafe_allow_html=True,
        )

with st.container(border=True):
    st.markdown("### Unggah data karyawan")
    st.caption(
        "Format CSV, maksimal 5 MB dan 20.000 baris. "
        "Kolom jam kerja menerima average_montly_hours maupun average_monthly_hours."
    )
    uploaded = st.file_uploader("Pilih file CSV", type=["csv"])

if uploaded is None:
    st.info("Pilih file CSV untuk memulai audit.")
    st.stop()
if not uploaded.name.lower().endswith(".csv"):
    st.error("File harus berformat .csv.")
    st.stop()
if uploaded.size > BATCH_MAX_BYTES:
    st.error("Ukuran file melebihi batas 5 MB.")
    st.stop()

try:
    dataframe = pd.read_csv(BytesIO(uploaded.getvalue()))
except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"CSV tidak dapat dibaca: {error}")
    st.stop()

if len(dataframe) > BATCH_MAX_ROWS:
    st.error("CSV melebihi batas 20.000 baris.")
    st.stop()

try:
    with st.spinner("Menjalankan validasi dan prediksi batch..."):
        artifacts = load_artifacts()
        batch_result = predict_batch(dataframe, artifacts)
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()
except ValueError as error:
    st.error(str(error))
    st.stop()

predictions = batch_result["predictions"]
rejected = batch_result["rejected"]
profile_by_cluster = {
    int(item["cluster"]): item for item in artifacts["profiles"]["clusters"]
}

if not predictions.empty:
    personas = []
    risks = []
    hr_recommendations = []
    for _, row in predictions.iterrows():
        profile = profile_by_cluster[int(row["Cluster"])]
        personas.append(profile["persona"])
        risks.append(profile["risk_level"])
        additions = recommend(
            profile["persona"],
            row.to_dict(),
            risk_level=profile["risk_level"],
        )
        combined = list(profile.get("strategy", [])) + additions["recommendations"]
        hr_recommendations.append(" | ".join(combined))
    predictions["Persona"] = personas
    predictions["Risk_Level"] = risks
    predictions["Rekomendasi_HR"] = hr_recommendations

st.markdown("### Ringkasan hasil audit")
total, valid, rejected_count = st.columns(3, gap="large")
total.metric("Total baris diproses", f"{len(dataframe):,}".replace(",", "."))
valid.metric("Baris valid", f"{len(predictions):,}".replace(",", "."))
rejected_count.metric("Baris ditolak", f"{len(rejected):,}".replace(",", "."))

if not predictions.empty:
    with st.container(border=True):
        st.markdown("### Distribusi klaster hasil batch")
        st.caption("Proporsi prediksi per persona pada data yang berhasil divalidasi.")
        st.plotly_chart(
            cluster_distribution(predictions),
            width="stretch",
            key="batch_cluster_distribution",
        )

    st.markdown("### Hasil prediksi")
    persona_options = sorted(predictions["Persona"].unique().tolist())
    risk_options = sorted(predictions["Risk_Level"].unique().tolist())
    persona_filter, risk_filter = st.columns(2, gap="large")
    with persona_filter:
        selected_personas = st.multiselect(
            "Filter persona",
            options=persona_options,
            default=persona_options,
            key="batch_persona_filter",
        )
    with risk_filter:
        selected_risks = st.multiselect(
            "Filter tingkat risiko",
            options=risk_options,
            default=risk_options,
            key="batch_risk_filter",
        )
    filtered_predictions = predictions.loc[
        predictions["Persona"].isin(selected_personas)
        & predictions["Risk_Level"].isin(selected_risks)
    ]
    display_predictions = filtered_predictions.head(100).copy()
    cluster_colors = {
        int(profile["cluster"]): profile["badge_color"]
        for profile in artifacts["profiles"]["clusters"]
    }

    def style_risk_cell(row: pd.Series) -> list[str]:
        color = cluster_colors.get(int(row["Cluster"]), "#1E3A8A")
        styles = [""] * len(row)
        if "Risk_Level" in row.index:
            risk_index = row.index.get_loc("Risk_Level")
            styles[risk_index] = (
                f"background-color: #F8FAFC; color: #1E293B; "
                f"border-left: 4px solid {color}; font-weight: 700"
            )
        return styles

    with st.container(border=True):
        st.caption(
            f"Menampilkan {len(display_predictions):,} dari "
            f"{len(filtered_predictions):,} baris sesuai filter (maksimal 100)."
        )
        if display_predictions.empty:
            st.info("Tidak ada baris yang cocok dengan filter pilihan.")
        else:
            st.dataframe(
                display_predictions.style.apply(style_risk_cell, axis=1).hide(
                    axis="index"
                ),
                width="stretch",
            )

    csv_result = predictions.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️  Unduh hasil audit CSV",
        data=csv_result,
        file_name="hasil_audit_karyawan.csv",
        mime="text/csv",
        width="stretch",
    )
else:
    st.info("Tidak ada baris valid untuk diprediksi.")

if not rejected.empty:
    with st.expander("Lihat Detail Baris yang Ditolak"):
        st.dataframe(rejected, hide_index=True, width="stretch")
