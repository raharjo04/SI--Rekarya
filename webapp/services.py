import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

from core.config import FEATURE_LABELS, FEATURES
from core.contracts import ArtifactBundle, ClusterProfile, SummaryStats


PERSONA_COLORS = {
    "Disengaged": "#B45309",
    "High Burnout": "#DC2626",
    "Senior Veteran": "#1E3A8A",
    "Engaged Stars": "#0D9488",
}
PERSONA_SHAPES = {
    "Disengaged": "triangle",
    "High Burnout": "circle",
    "Senior Veteran": "rectRot",
    "Engaged Stars": "rect",
}
RISK_CLASSES = {
    "Sangat Tinggi": "risk-high",
    "Tinggi": "risk-high",
    "Sedang": "risk-medium",
    "Rendah": "risk-low",
}


def format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{float(value):,.{decimals}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def format_percent(value: float, decimals: int = 1) -> str:
    return f"{format_number(value, decimals)}%"


def risk_class(value: str) -> str:
    return RISK_CLASSES.get(value, "risk-neutral")


def profile_color(profile: ClusterProfile) -> str:
    return PERSONA_COLORS.get(profile["persona"], profile["badge_color"])


def build_summary_insights(
    dataframe: pd.DataFrame,
    stats: SummaryStats,
) -> list[str]:
    project_summary = stats["project_summary"]
    insights: list[str] = []
    if not project_summary.empty:
        highest = project_summary.loc[project_summary["turnover_rate"].idxmax()]
        largest = project_summary.loc[project_summary["jumlah_karyawan"].idxmax()]
        insights.append(
            f"Karyawan dengan {int(highest['jumlah_proyek'])} proyek paling "
            f"banyak keluar ({format_percent(highest['turnover_rate'] * 100)}; "
            f"n={format_number(highest['jumlah_karyawan'])})."
        )
        insights.append(
            f"Kelompok terbesar adalah karyawan dengan "
            f"{int(largest['jumlah_proyek'])} proyek "
            f"(n={format_number(largest['jumlah_karyawan'])})."
        )

    high_load = build_high_load_metrics(dataframe)
    if high_load["count"]:
        insights.append(
            f"{format_number(high_load['count'])} karyawan bekerja di atas 250 jam "
            f"dengan kepuasan di bawah 0,40; "
            f"{format_percent(float(high_load['exit_rate']))} di antaranya pernah keluar."
        )
    return insights[:3]


def build_workload_bubbles(dataframe: pd.DataFrame) -> dict[str, Any]:
    hour_edges = [96, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 311]
    satisfaction_edges = [value / 10 for value in range(11)]
    satisfaction_edges[-1] = 1.000001
    frame = pd.DataFrame(
        {
            "hours": pd.to_numeric(
                dataframe["average_montly_hours"], errors="coerce"
            ),
            "satisfaction": pd.to_numeric(
                dataframe["satisfaction_level"], errors="coerce"
            ),
            "left": pd.to_numeric(dataframe["left"], errors="coerce"),
        }
    ).dropna()
    frame = frame.loc[frame["left"].isin([0, 1])].copy()
    frame["hour_bin"] = pd.cut(
        frame["hours"],
        bins=hour_edges,
        labels=False,
        right=False,
        include_lowest=True,
    )
    frame["satisfaction_bin"] = pd.cut(
        frame["satisfaction"],
        bins=satisfaction_edges,
        labels=False,
        right=False,
        include_lowest=True,
    )
    grouped = (
        frame.dropna(subset=["hour_bin", "satisfaction_bin"])
        .groupby(["hour_bin", "satisfaction_bin"], observed=True)
        .agg(count=("left", "size"), exits=("left", "sum"))
        .reset_index()
    )
    bubbles = []
    for row in grouped.to_dict(orient="records"):
        hour_bin = int(row["hour_bin"])
        satisfaction_bin = int(row["satisfaction_bin"])
        count = int(row["count"])
        exits = int(row["exits"])
        exit_rate = exits / count * 100
        if exit_rate <= 15:
            color = "#0F766E"
        elif exit_rate <= 30:
            color = "#B45309"
        else:
            color = "#B91C1C"
        hour_start, hour_end = hour_edges[hour_bin : hour_bin + 2]
        satisfaction_start, satisfaction_end = satisfaction_edges[
            satisfaction_bin : satisfaction_bin + 2
        ]
        bubbles.append(
            {
                "x": (hour_start + hour_end) / 2,
                "y": (satisfaction_start + satisfaction_end) / 2,
                "r": min(18, max(4, 3 + math.sqrt(count) * 1.2)),
                "count": count,
                "exits": exits,
                "exitRate": exit_rate,
                "color": color,
                "hourRange": (
                    f"{format_number(hour_start)}–{format_number(hour_end)} jam"
                ),
                "satisfactionRange": (
                    f"{format_number(satisfaction_start, 1)}–"
                    f"{format_number(satisfaction_end, 1)}"
                ),
            }
        )
    return {"points": bubbles, "total_count": int(grouped["count"].sum())}


def build_high_load_metrics(dataframe: pd.DataFrame) -> dict[str, float | int]:
    high_load = dataframe.loc[
        (pd.to_numeric(dataframe["average_montly_hours"], errors="coerce") > 250)
        & (pd.to_numeric(dataframe["satisfaction_level"], errors="coerce") < 0.4)
    ]
    exits = pd.to_numeric(high_load["left"], errors="coerce")
    return {
        "count": int(len(high_load)),
        "exit_rate": float(exits.mean() * 100) if not high_load.empty else 0.0,
    }


def build_persona_cards(
    profiles: list[ClusterProfile],
    overall_turnover: float,
) -> list[dict[str, Any]]:
    cards = []
    for profile in profiles:
        means = profile["means"]
        satisfaction = float(means["satisfaction_level"])
        turnover_percent = float(profile["turnover_rate"]) * 100
        difference = turnover_percent - overall_turnover
        if satisfaction < 0.35:
            satisfaction_text = "kepuasan cenderung rendah"
        elif satisfaction < 0.65:
            satisfaction_text = "kepuasan berada di tingkat menengah"
        else:
            satisfaction_text = "kepuasan cenderung tinggi"
        if difference > 0:
            benchmark_note = (
                f"Tingkat keluar {format_number(difference, 1)} poin persentase "
                f"di atas rata-rata keseluruhan "
                f"({format_percent(overall_turnover)})."
            )
        elif difference < 0:
            benchmark_note = (
                f"Tingkat keluar {format_number(abs(difference), 1)} poin persentase "
                f"di bawah rata-rata keseluruhan "
                f"({format_percent(overall_turnover)})."
            )
        else:
            benchmark_note = "Tingkat keluar sama dengan rata-rata keseluruhan."
        cards.append(
            {
                **profile,
                "color": profile_color(profile),
                "risk_class": risk_class(profile["risk_level"]),
                "turnover_percent": turnover_percent,
                "benchmark_note": benchmark_note,
                "description": (
                    f"Karyawan di kelompok ini memiliki {satisfaction_text}, "
                    f"bekerja rata-rata "
                    f"{format_number(means['average_montly_hours'])} jam per bulan, "
                    f"dan menangani sekitar "
                    f"{format_number(means['number_project'], 1)} proyek."
                ),
            }
        )
    return cards


def build_map_datasets(
    dataframe: pd.DataFrame,
    artifacts: ArtifactBundle,
    added_point: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    sample = dataframe.sample(n=min(2000, len(dataframe)), random_state=42)
    features = sample[FEATURES]
    scaled = artifacts["scaler"].transform(features)
    coordinates = artifacts["pca"].transform(scaled)
    clusters = artifacts["kmeans"].predict(scaled)
    profiles = artifacts["profiles"]["clusters"]
    profile_by_cluster = {int(item["cluster"]): item for item in profiles}

    datasets: list[dict[str, Any]] = []
    for profile in profiles:
        cluster = int(profile["cluster"])
        mask = clusters == cluster
        points = coordinates[mask]
        persona = str(profile["persona"])
        color = profile_color(profile)
        datasets.append(
            {
                "label": persona,
                "data": [
                    {"x": float(point[0]), "y": float(point[1])}
                    for point in points
                ],
                "backgroundColor": color,
                "pointStyle": PERSONA_SHAPES.get(persona, "circle"),
                "pointRadius": 3,
                "pointHoverRadius": 6,
                "pointBorderColor": "#FFFFFF",
                "pointBorderWidth": 0.5,
                "employeeCount": int(profile["count"]),
                "teamPercentage": float(profile["percentage"]),
                "turnoverPercent": float(profile["turnover_rate"]) * 100,
                "riskLevel": str(profile["risk_level"]),
            }
        )

    center_coordinates = artifacts["pca"].transform(
        artifacts["kmeans"].cluster_centers_
    )
    for cluster, point in enumerate(center_coordinates):
        profile = profile_by_cluster[cluster]
        persona = str(profile["persona"])
        datasets.append(
            {
                "label": f"Pusat kelompok {persona}",
                "centerLabel": persona,
                "isCenter": True,
                "data": [{"x": float(point[0]), "y": float(point[1])}],
                "backgroundColor": profile_color(profile),
                "borderColor": "#FFFFFF",
                "pointStyle": PERSONA_SHAPES.get(persona, "circle"),
                "pointRadius": 9,
                "pointBorderWidth": 2,
                "employeeCount": int(profile["count"]),
                "teamPercentage": float(profile["percentage"]),
                "turnoverPercent": float(profile["turnover_rate"]) * 100,
                "riskLevel": str(profile["risk_level"]),
            }
        )

    if added_point is not None:
        datasets.append(
            {
                "label": "Karyawan yang dianalisis",
                "isEmployee": True,
                "data": [
                    {
                        "x": float(added_point["pca_x"]),
                        "y": float(added_point["pca_y"]),
                    }
                ],
                "backgroundColor": "#B45309",
                "borderColor": "#FFFFFF",
                "pointStyle": "star",
                "pointRadius": 13,
                "pointBorderWidth": 3,
            }
        )
    return datasets


def build_comparison(
    employee_values: Mapping[str, float],
    group_means: Mapping[str, float],
) -> dict[str, Any]:
    input_values = [float(employee_values[feature]) for feature in FEATURES]
    means = [float(group_means[feature]) for feature in FEATURES]
    relative = [
        value / mean * 100 if mean else 0.0
        for value, mean in zip(input_values, means)
    ]
    return {
        "labels": [FEATURE_LABELS[feature] for feature in FEATURES],
        "relative_input": relative,
        "group_average": [100.0] * len(FEATURES),
        "input_values": input_values,
        "group_means": means,
    }


def build_technical_evaluation(
    artifacts: ArtifactBundle,
) -> dict[str, Any]:
    variance = getattr(artifacts["pca"], "explained_variance_ratio_", [])
    explained_variance = float(sum(variance[:2])) if len(variance) >= 2 else 0.0
    return {
        "optimal_k": int(artifacts["profiles"]["optimal_k"]),
        "explained_variance": explained_variance * 100,
        "evaluation": artifacts["profiles"]["evaluation"],
    }
