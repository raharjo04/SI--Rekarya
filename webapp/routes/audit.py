from io import BytesIO
from numbers import Real

import pandas as pd
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from core.artifacts import load_artifacts
from core.config import BATCH_MAX_BYTES, BATCH_MAX_ROWS
from core.predictor import predict_batch
from webapp.common import render_page
from webapp.downloads import download_store
from webapp.services import format_number, profile_color


router = APIRouter()
INTERNAL_COLUMNS = {
    "Cluster",
    "badge_color",
    "Jarak centroid",
    "PCA1",
    "PCA2",
    "Peringatan",
}


def _audit_response(
    request: Request,
    *,
    current_step: int,
    error: str | None = None,
    result: dict | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        "current_step": current_step,
        "error": error,
        "result": result,
        "format_number": format_number,
    }
    if request.headers.get("HX-Request") == "true":
        return render_page(
            request,
            "partials/audit_results.html",
            **context,
            status_code=status_code,
        )
    return render_page(
        request,
        "audit.html",
        title="Audit Data Massal",
        description=(
            "Validasi data karyawan dari CSV dan tinjau hasil kelompok beserta risikonya."
        ),
        **context,
        status_code=status_code,
    )


def _format_rows(dataframe: pd.DataFrame) -> list[dict[str, str]]:
    rows = []
    for row in dataframe.to_dict(orient="records"):
        formatted: dict[str, str] = {}
        for column, value in row.items():
            if pd.isna(value):
                formatted[column] = "—"
            elif isinstance(value, Real) and not isinstance(value, bool):
                numeric = float(value)
                if numeric.is_integer():
                    formatted[column] = format_number(numeric)
                else:
                    formatted[column] = (
                        format_number(numeric, 2).rstrip("0").rstrip(",")
                    )
            else:
                formatted[column] = str(value)
        rows.append(formatted)
    return rows


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "audit.html",
        title="Audit Data Massal",
        description=(
            "Validasi data karyawan dari CSV dan tinjau hasil kelompok beserta risikonya."
        ),
        current_step=1,
        error=None,
        result=None,
    )


@router.post("/audit", response_class=HTMLResponse)
def audit_csv(
    request: Request,
    file: UploadFile = File(...),
) -> HTMLResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        return _audit_response(
            request,
            current_step=2,
            error="File harus berformat .csv.",
            status_code=400,
        )
    if file.size is not None and file.size > BATCH_MAX_BYTES:
        return _audit_response(
            request,
            current_step=2,
            error="Ukuran file melebihi batas 5 MB.",
            status_code=413,
        )

    content = file.file.read(BATCH_MAX_BYTES + 1)
    if len(content) > BATCH_MAX_BYTES:
        return _audit_response(
            request,
            current_step=2,
            error="Ukuran file melebihi batas 5 MB.",
            status_code=413,
        )
    if not content:
        return _audit_response(
            request,
            current_step=2,
            error="File CSV tidak berisi data.",
            status_code=400,
        )

    try:
        dataframe = pd.read_csv(
            BytesIO(content),
            nrows=BATCH_MAX_ROWS + 1,
            encoding="utf-8-sig",
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return _audit_response(
            request,
            current_step=2,
            error="CSV tidak dapat dibaca. Periksa pemisah kolom dan encoding UTF-8.",
            status_code=400,
        )

    if len(dataframe) > BATCH_MAX_ROWS:
        return _audit_response(
            request,
            current_step=2,
            error="CSV melebihi batas 20.000 baris data.",
            status_code=413,
        )
    if dataframe.empty:
        return _audit_response(
            request,
            current_step=2,
            error="CSV harus berisi setidaknya satu baris data.",
            status_code=400,
        )

    try:
        artifacts = load_artifacts()
        batch_result = predict_batch(dataframe, artifacts)
    except (FileNotFoundError, ValueError) as error:
        return _audit_response(
            request,
            current_step=2,
            error=str(error),
            status_code=422,
        )

    predictions = batch_result["predictions"]
    rejected = batch_result["rejected"]
    export_token = None
    distribution = []
    display_rows = []
    if not predictions.empty:
        profiles = artifacts["profiles"]["clusters"]
        color_by_persona = {
            str(profile["persona"]): profile_color(profile) for profile in profiles
        }
        counts = predictions.groupby("Persona", as_index=False).size()
        distribution = [
            {
                "label": str(row["Persona"]),
                "count": int(row["size"]),
                "color": color_by_persona[str(row["Persona"])],
            }
            for _, row in counts.iterrows()
        ]
        display_columns = [
            column for column in predictions.columns if column not in INTERNAL_COLUMNS
        ]
        display_rows = _format_rows(
            predictions[display_columns]
            .head(100)
            .rename(
                columns={
                    "satisfaction_level": "Tingkat kepuasan",
                    "last_evaluation": "Evaluasi terakhir",
                    "number_project": "Jumlah proyek",
                    "average_montly_hours": "Jam kerja bulanan",
                    "average_monthly_hours": "Jam kerja bulanan",
                    "time_spend_company": "Masa kerja (tahun)",
                }
            )
        )
        export = predictions[display_columns].to_csv(index=False).encode("utf-8-sig")
        export_token = download_store.create(export)

    rejected_rows = _format_rows(rejected.head(100))
    result = {
        "processed_count": len(predictions),
        "rejected_count": len(rejected),
        "total_count": len(dataframe),
        "display_rows": display_rows,
        "rejected_rows": rejected_rows,
        "distribution": distribution,
        "distribution_total": sum(item["count"] for item in distribution),
        "download_url": (
            f"/audit/download/{export_token}" if export_token is not None else None
        ),
        "row_limit": min(len(predictions), 100),
    }
    return _audit_response(
        request,
        current_step=3,
        result=result,
    )


@router.get("/audit/download/{token}")
def download_audit_result(token: str) -> Response:
    content = download_store.get(token)
    if content is None:
        return Response(
            content="Tautan unduhan sudah kedaluwarsa. Jalankan audit kembali.",
            status_code=404,
            media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="hasil_audit_karyawan.csv"'
        },
    )


def audit_template_csv() -> bytes:
    columns = [
        "satisfaction_level",
        "last_evaluation",
        "number_project",
        "average_montly_hours",
        "time_spend_company",
    ]
    return (",".join(columns) + "\n").encode("utf-8")


@router.get("/audit/template.csv")
def download_audit_template() -> Response:
    return Response(
        content=audit_template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="template_audit_karyawan.csv"'
        },
    )
