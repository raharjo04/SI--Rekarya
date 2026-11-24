from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from core.config import FEATURE_BOUNDS, FEATURES, INTEGER_FEATURES
from core.artifacts import load_artifacts
from core.contracts import (
    ArtifactBundle,
    BatchPredictionResult,
    ClusterProfile,
    FeatureValues,
    PredictionResult,
    PredictorInput,
    ValidateInputResult,
)


MONTHLY_HOURS_ALIAS = "average_monthly_hours"


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    if MONTHLY_HOURS_ALIAS in normalized.columns:
        if "average_montly_hours" not in normalized.columns:
            normalized = normalized.rename(
                columns={MONTHLY_HOURS_ALIAS: "average_montly_hours"}
            )
    return normalized


def _validated_record(data: Mapping[str, Any]) -> tuple[FeatureValues, list[str]]:
    normalized = _normalize_columns(pd.DataFrame([dict(data)]))
    missing = [feature for feature in FEATURES if feature not in normalized.columns]
    if missing:
        raise ValueError(f"Kolom fitur wajib tidak tersedia: {', '.join(missing)}.")

    clean: dict[str, float] = {}
    for feature in FEATURES:
        value = pd.to_numeric(normalized.iloc[0][feature], errors="coerce")
        if pd.isna(value) or not np.isfinite(float(value)):
            raise ValueError(f"{feature} harus berisi angka yang valid.")
        lower, upper = FEATURE_BOUNDS[feature]
        if value < lower or value > upper:
            raise ValueError(
                f"{feature} harus berada pada rentang {lower} sampai {upper}."
            )
        if feature in INTEGER_FEATURES and not float(value).is_integer():
            raise ValueError(f"{feature} harus berupa bilangan bulat.")
        clean[feature] = float(value)

    warnings = []
    hours = clean["average_montly_hours"]
    if hours < 120 or hours > 250:
        warnings.append(
            "Jam kerja bulanan berada di luar kisaran umum 120–250 jam."
        )
    return clean, warnings


def _profiles_by_cluster(
    artifacts: ArtifactBundle,
) -> dict[int, ClusterProfile]:
    return {
        int(profile["cluster"]): profile
        for profile in artifacts["profiles"]["clusters"]
    }


def validate_input(data: PredictorInput) -> ValidateInputResult:
    """Validate one employee record and return a feature-ordered frame and warnings."""
    clean, warnings = _validated_record(data)
    return pd.DataFrame([clean], columns=FEATURES), warnings


def _predict_frame(
    feature_frame: pd.DataFrame, artifacts: ArtifactBundle
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scaled = artifacts["scaler"].transform(feature_frame[FEATURES])
    clusters = artifacts["kmeans"].predict(scaled)
    centers = artifacts["kmeans"].cluster_centers_[clusters]
    distances = np.linalg.norm(scaled - centers, axis=1)
    coordinates = artifacts["pca"].transform(scaled)
    return clusters, distances, coordinates


def predict_one(
    data: PredictorInput, artifacts: ArtifactBundle | None = None
) -> PredictionResult:
    if artifacts is None:
        artifacts = load_artifacts()
    clean, warnings = _validated_record(data)
    frame = pd.DataFrame([clean], columns=FEATURES)
    clusters, distances, coordinates = _predict_frame(frame, artifacts)
    cluster = int(clusters[0])
    profile = _profiles_by_cluster(artifacts)[cluster]
    return {
        "cluster": cluster,
        "persona": profile["persona"],
        "risk_level": profile["risk_level"],
        "badge_color": profile["badge_color"],
        "distance": float(distances[0]),
        "pca_x": float(coordinates[0, 0]),
        "pca_y": float(coordinates[0, 1]),
        "features": clean,
        "warnings": warnings,
    }


def predict_batch(
    dataframe: pd.DataFrame, artifacts: ArtifactBundle | None = None
) -> BatchPredictionResult:
    """Predict valid rows while retaining rejected input rows and their reasons."""
    if artifacts is None:
        artifacts = load_artifacts()
    original = dataframe.copy()
    source = _normalize_columns(original)
    missing = [feature for feature in FEATURES if feature not in source.columns]
    if missing:
        raise ValueError(f"Kolom fitur wajib tidak tersedia: {', '.join(missing)}.")

    valid_records: list[dict[str, float]] = []
    valid_positions: list[int] = []
    rejected: list[dict[str, Any]] = []
    warnings_by_position: dict[int, str] = {}

    for position, (_, row) in enumerate(source.iterrows()):
        try:
            clean, warnings = _validated_record(row.to_dict())
        except ValueError as error:
            rejected.append(
                {
                    "Nomor baris": position + 2,
                    "Alasan": str(error),
                    **original.iloc[position].to_dict(),
                }
            )
            continue
        valid_records.append(clean)
        valid_positions.append(position)
        warnings_by_position[position] = "; ".join(warnings)

    if valid_records:
        feature_frame = pd.DataFrame(valid_records, columns=FEATURES)
        clusters, distances, coordinates = _predict_frame(feature_frame, artifacts)
        profiles_by_cluster = _profiles_by_cluster(artifacts)
        assigned_profiles = [profiles_by_cluster[int(cluster)] for cluster in clusters]
        output = original.iloc[valid_positions].copy().reset_index(drop=True)
        output["Cluster"] = clusters.astype(int)
        output["Persona"] = [profile["persona"] for profile in assigned_profiles]
        output["Risk_Level"] = [profile["risk_level"] for profile in assigned_profiles]
        output["badge_color"] = [
            profile["badge_color"] for profile in assigned_profiles
        ]
        output["Jarak centroid"] = distances
        output["PCA1"] = coordinates[:, 0]
        output["PCA2"] = coordinates[:, 1]
        output["Peringatan"] = [
            warnings_by_position[position] for position in valid_positions
        ]
    else:
        output = original.iloc[0:0].copy()
        for column in (
            "Cluster",
            "Persona",
            "Risk_Level",
            "badge_color",
            "Jarak centroid",
            "PCA1",
            "PCA2",
            "Peringatan",
        ):
            output[column] = pd.Series(dtype="object")

    return {
        "predictions": output,
        "rejected": pd.DataFrame(rejected),
    }
