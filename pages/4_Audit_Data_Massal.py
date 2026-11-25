from io import BytesIO

import pandas as pd
import streamlit as st

from core.artifacts import load_artifacts
from core.charts import cluster_distribution
from core.config import (
    BATCH_MAX_BYTES,
    BATCH_MAX_ROWS,
    FEATURE_LABELS,
)
from core.predictor import predict_batch
from core.recommender import recommend
from core.ui_theme import inject_custom_css, page_header


def _format_number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _show_stepper(placeholder, active_step: int) -> None:
    labels = ("Unduh template", "Unggah CSV", "Tinjau hasil")
    steps = []
    for number, label in enumerate(labels, start=1):
        state = "si-step-active" if number == active_step else ""
        if number < active_step:
            state = "si-step-complete"
        steps.append(
            f'<div class="si-step {state}">'
            f'<span class="si-step-number">{number}</span>{label}</div>'
        )
    placeholder.markdown(
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);'
        'gap:12px;margin:12px 0 20px">'
        + "".join(steps)
        + "</div>",
        unsafe_allow_html=True,
    )


inject_custom_css()
page_header(
    "Audit Data Massal",
    "Validasi data karyawan dari CSV dan tinjau hasil kelompok beserta risikonya.",
)

template = pd.DataFrame(
    columns=[
        "satisfaction_level",
        "last_evaluation",
        "number_project",
        "average_montly_hours",
        "time_spend_company",
    ]
)

with st.container(border=True):
    st.markdown("### Langkah 1 — Siapkan template")
    st.caption(
        "Gunakan nama kolom dan urutan data di bawah. Contoh ini hanya menunjukkan "
        "format, bukan data karyawan sebenarnya."
    )
    st.code(
        "satisfaction_level,last_evaluation,number_project,"
        "average_montly_hours,time_spend_company\n"
        "0.72,0.81,4,201,3\n"
        "0.38,0.64,6,258,5",
        language="csv",
    )
    st.download_button(
        "Unduh template CSV",
        data=template.to_csv(index=False).encode("utf-8"),
        file_name="template_audit_karyawan.csv",
        mime="text/csv",
        width="stretch",
    )

stepper = st.empty()
with st.container(border=True):
    st.markdown("### Langkah 2 — Unggah data")
    st.caption(
        "Maksimal 5 MB dan 20.000 baris. Kolom jam kerja menerima "
        "average_montly_hours maupun average_monthly_hours."
    )
    uploaded = st.file_uploader("Pilih file CSV", type=["csv"])

if uploaded is None:
    _show_stepper(stepper, 1)
    st.info("Pilih file CSV untuk melanjutkan audit.")
    st.stop()

_show_stepper(stepper, 2)
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

_show_stepper(stepper, 3)
with st.container(border=True):
    st.markdown("### Ringkasan hasil audit")
    processed, rejected_count = st.columns(2, gap="large")
    processed.metric(
        "Baris berhasil diproses",
        f"{len(predictions):,}".replace(",", "."),
    )
    rejected_count.metric(
        "Baris ditolak",
        f"{len(rejected):,}".replace(",", "."),
    )

if not predictions.empty:
    with st.container(border=True):
        st.markdown("### Distribusi persona")
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

    internal_columns = {
        "Cluster",
        "badge_color",
        "Jarak centroid",
        "PCA1",
        "PCA2",
        "Peringatan",
    }
    display_columns = [
        column for column in predictions.columns if column not in internal_columns
    ]
    display_predictions = filtered_predictions[display_columns].head(100).copy()
    display_predictions = display_predictions.rename(
        columns={
            **FEATURE_LABELS,
            "average_monthly_hours": FEATURE_LABELS["average_montly_hours"],
        }
    )

    risk_style = {
        "Sangat Tinggi": ("#FEE2E2", "#991B1B", "#DC2626"),
        "Tinggi": ("#FEE2E2", "#991B1B", "#DC2626"),
        "Sedang": ("#FEF3C7", "#78350F", "#B45309"),
        "Rendah": ("#CCFBF1", "#115E59", "#0D9488"),
    }

    def style_risk_cell(row: pd.Series) -> list[str]:
        styles = [""] * len(row)
        if "Risk_Level" in row.index:
            risk_index = row.index.get_loc("Risk_Level")
            background, foreground, border = risk_style.get(
                str(row["Risk_Level"]),
                ("#E2E8F0", "#334155", "#64748B"),
            )
            styles[risk_index] = (
                f"background-color: {background}; color: {foreground}; "
                f"border-left: 4px solid {border}; font-weight: 700"
            )
        return styles

    with st.container(border=True):
        st.caption(
            f"Menampilkan {_format_number(len(display_predictions))} dari "
            f"{_format_number(len(filtered_predictions))} baris sesuai filter "
            "(maksimal 100)."
        )
        if display_predictions.empty:
            st.info("Tidak ada baris yang cocok dengan filter pilihan.")
        else:
            st.dataframe(
                display_predictions.style.apply(style_risk_cell, axis=1).format(
                    precision=2,
                    thousands=".",
                    decimal=",",
                ).hide(axis="index"),
                width="stretch",
            )

    export_columns = [
        column for column in predictions.columns if column not in internal_columns
    ]
    csv_result = predictions[export_columns].to_csv(index=False).encode("utf-8-sig")
    with st.container(border=True):
        st.markdown("### Unduh hasil audit")
        st.download_button(
            "Unduh hasil audit CSV",
            data=csv_result,
            file_name="hasil_audit_karyawan.csv",
            mime="text/csv",
            width="stretch",
        )
else:
    st.info("Tidak ada baris valid untuk diprediksi.")

if not rejected.empty:
    with st.expander("Lihat detail baris yang ditolak"):
        st.dataframe(rejected, hide_index=True, width="stretch")
