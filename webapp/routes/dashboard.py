from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from core.artifacts import load_artifacts
from core.config import FEATURES
from core.data import load_dataset, summary_stats
from core.predictor import predict_one
from core.recommender import recommend
from webapp.common import render_page
from webapp.services import (
    build_comparison,
    build_high_load_metrics,
    build_map_datasets,
    build_persona_cards,
    build_summary_insights,
    build_technical_evaluation,
    build_workload_bubbles,
    format_number,
    format_percent,
    profile_color,
    risk_class,
)


router = APIRouter()


def _error(
    request: Request,
    message: str,
    status_code: int = 503,
    partial: bool = False,
) -> HTMLResponse:
    if partial:
        return render_page(
            request,
            "partials/error_message.html",
            message=message,
            status_code=status_code,
        )
    return render_page(
        request,
        "error.html",
        title="Halaman belum dapat ditampilkan",
        message=message,
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse)
def summary_page(request: Request) -> HTMLResponse:
    try:
        dataframe = load_dataset()
        stats = summary_stats(dataframe)
        if stats["project_summary"].empty:
            raise ValueError("Tidak ada data jumlah proyek yang valid untuk diringkas.")
    except (FileNotFoundError, ValueError) as error:
        return _error(request, str(error))

    highest_project_turnover = stats["project_summary"].loc[
        stats["project_summary"]["turnover_rate"].idxmax()
    ]
    high_load = build_high_load_metrics(dataframe)
    overall_turnover = float(stats["turnover_rate"]) * 100
    return render_page(
        request,
        "summary.html",
        title="Ringkasan SDM",
        description=(
            "Gambaran tenaga kerja, pola beban kerja, dan risiko karyawan keluar."
        ),
        total=format_number(stats["total_karyawan"]),
        turnover=format_percent(stats["turnover_rate"] * 100),
        satisfaction=format_number(stats["rata_kepuasan"], 2),
        monthly_hours=format_number(stats["rata_jam_bulanan"]) + " jam",
        insights=build_summary_insights(dataframe, stats),
        project_heading=(
            f"Karyawan dengan "
            f"{int(highest_project_turnover['jumlah_proyek'])} proyek "
            "paling banyak keluar"
        ),
        project_chart={
            "labels": [
                f"{int(value)} proyek"
                for value in stats["project_summary"]["jumlah_proyek"]
            ],
            "rates": [
                float(value) * 100
                for value in stats["project_summary"]["turnover_rate"]
            ],
            "counts": [
                int(value)
                for value in stats["project_summary"]["jumlah_karyawan"]
            ],
            "overall_rate": overall_turnover,
        },
        workload_chart=build_workload_bubbles(dataframe),
        workload_summary={
            "count": high_load["count"],
            "exit_rate": format_percent(float(high_load["exit_rate"])),
            "overall_rate": format_percent(overall_turnover),
        },
        format_number=format_number,
        format_percent=format_percent,
    )


@router.get("/personas", response_class=HTMLResponse)
def personas_page(request: Request) -> HTMLResponse:
    try:
        dataframe = load_dataset()
        artifacts = load_artifacts()
        missing = [feature for feature in FEATURES if feature not in dataframe]
        if missing:
            raise ValueError(
                f"Kolom dataset tidak tersedia: {', '.join(missing)}."
            )
        profiles = artifacts["profiles"]["clusters"]
        map_datasets = build_map_datasets(dataframe, artifacts)
        technical = build_technical_evaluation(artifacts)
        overall_turnover = float(summary_stats(dataframe)["turnover_rate"]) * 100
    except (FileNotFoundError, ValueError) as error:
        return _error(request, str(error))

    return render_page(
        request,
        "personas.html",
        title="Persona & Peta",
        description=(
            "Kenali karakteristik empat kelompok karyawan dan pola kemiripannya."
        ),
        personas=build_persona_cards(
            profiles,
            overall_turnover,
        ),
        map_chart=map_datasets,
        map_count=min(2000, len(dataframe)),
        total_count=len(dataframe),
        technical=technical,
        format_number=format_number,
        format_percent=format_percent,
    )


def _detection_context(
    request: Request,
    input_data: dict[str, Any],
    submitted_values: dict[str, Any],
    hx_request: bool,
) -> HTMLResponse:
    try:
        artifacts = load_artifacts()
        dataframe = load_dataset()
        missing = [feature for feature in FEATURES if feature not in dataframe]
        if missing:
            raise ValueError(
                f"Kolom dataset tidak tersedia: {', '.join(missing)}."
            )
        result = predict_one(input_data, artifacts)
    except (FileNotFoundError, ValueError) as error:
        if hx_request:
            return _error(request, str(error), status_code=422, partial=True)
        return render_page(
            request,
            "detect.html",
            title="Deteksi Karyawan",
            description=(
                "Bandingkan karakteristik karyawan dengan kelompok yang paling serupa."
            ),
            values=submitted_values,
            error=str(error),
            result=None,
        )

    profile = next(
        item
        for item in artifacts["profiles"]["clusters"]
        if int(item["cluster"]) == result["cluster"]
    )
    recommendation = recommend(
        profile["persona"],
        input_data,
        risk_level=profile["risk_level"],
    )
    recommendations = list(recommendation["recommendations"])
    recommendations.extend(
        item
        for item in profile.get("strategy", [])
        if item not in recommendations
    )
    context = {
        "profile": {
            **profile,
            "color": profile_color(profile),
            "risk_class": risk_class(profile["risk_level"]),
            "historical_exits": round(float(profile["turnover_rate"]) * 100),
        },
        "recommendations": recommendations,
        "policy_note": recommendation["policy_note"],
        "triggered_rules": recommendation["triggered_rules"],
        "warnings": result["warnings"],
        "comparison": build_comparison(result["features"], profile["means"]),
        "map_chart": build_map_datasets(
            dataframe,
            artifacts,
            added_point=result,
        ),
        "persona_legend": [
            {"persona": item["persona"], "color": profile_color(item)}
            for item in artifacts["profiles"]["clusters"]
        ],
        "technical": {
            "distance": format_number(result["distance"], 3),
            "satisfaction": format_number(
                result["features"]["satisfaction_level"], 2
            ),
        },
    }
    if hx_request:
        return render_page(
            request,
            "partials/detection_result.html",
            **context,
        )
    return render_page(
        request,
        "detect.html",
        title="Deteksi Karyawan",
        description=(
            "Bandingkan karakteristik karyawan dengan kelompok yang paling serupa."
        ),
        values=submitted_values,
        result=context,
        error=None,
    )


@router.get("/detect", response_class=HTMLResponse)
def detection_page(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "detect.html",
        title="Deteksi Karyawan",
        description=(
            "Bandingkan karakteristik karyawan dengan kelompok yang paling serupa."
        ),
        values={
            "satisfaction_level": "0.50",
            "last_evaluation": "0.70",
            "number_project": "4",
            "average_montly_hours": "160",
            "time_spend_company": "3",
            "promotion_last_5years": False,
        },
        result=None,
        error=None,
    )


@router.post("/detect", response_class=HTMLResponse)
def detect_employee(
    request: Request,
    satisfaction_level: str = Form(...),
    last_evaluation: str = Form(...),
    number_project: str = Form(...),
    average_montly_hours: str = Form(...),
    time_spend_company: str = Form(...),
    promotion_last_5years: str | None = Form(default=None),
) -> HTMLResponse:
    hx_request = request.headers.get("HX-Request") == "true"
    values = {
        "satisfaction_level": satisfaction_level,
        "last_evaluation": last_evaluation,
        "number_project": number_project,
        "average_montly_hours": average_montly_hours,
        "time_spend_company": time_spend_company,
        "promotion_last_5years": promotion_last_5years is not None,
    }
    try:
        input_data: dict[str, Any] = {
            "satisfaction_level": float(satisfaction_level),
            "last_evaluation": float(last_evaluation),
            "number_project": int(number_project),
            "average_montly_hours": float(average_montly_hours),
            "time_spend_company": int(time_spend_company),
            "promotion_last_5years": promotion_last_5years is not None,
        }
    except ValueError:
        message = "Isi semua nilai dengan angka yang valid."
        if hx_request:
            return _error(request, message, status_code=422, partial=True)
        return render_page(
            request,
            "detect.html",
            title="Deteksi Karyawan",
            description=(
                "Bandingkan karakteristik karyawan dengan kelompok yang paling serupa."
            ),
            values=values,
            result=None,
            error=message,
        )
    return _detection_context(request, input_data, values, hx_request)
