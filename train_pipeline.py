import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from core.config import ARTIFACTS_DIR, DATASET_PATH, FEATURES


RANDOM_STATE = 42
OPTIMAL_K = 4
EVALUATED_K = range(2, 9)
SILHOUETTE_SAMPLE_SIZE = 3000
PERSONA_STRATEGIES = {
    "High Burnout": [
        "Redistribusi proyek dan pantau beban kerja untuk mencegah burnout.",
        "Tinjau jam lembur, cuti pemulihan, kompensasi, dan peluang promosi.",
    ],
    "Disengaged": [
        "Jadwalkan sesi coaching 1-on-1 dan asesmen kecocokan peran.",
        "Susun rencana reskilling dan tindak lanjut keterlibatan.",
    ],
    "Engaged Stars": [
        "Pertimbangkan jalur leadership fast-track dan insentif retensi.",
        "Tawarkan kesempatan mentoring dan proyek berdampak tinggi.",
    ],
    "Senior Veteran": [
        "Tinjau jenjang jabatan dan tunjangan senioritas.",
        "Pertimbangkan rotasi ke proyek strategis dan berbagi keahlian.",
    ],
}
RISK_COLORS = {
    "Rendah": "#0D9488",
    "Sedang": "#F59E0B",
    "Tinggi": "#EA580C",
    "Sangat Tinggi": "#DC2626",
}


def load_training_data(path: Path = DATASET_PATH) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {path}. "
            "Letakkan HR_comma_sep.csv di root proyek atau folder data/."
        )
    dataframe = pd.read_csv(path)
    missing = [feature for feature in FEATURES if feature not in dataframe.columns]
    if missing:
        raise ValueError(f"Kolom fitur dataset tidak tersedia: {', '.join(missing)}.")
    if dataframe.empty:
        raise ValueError("Dataset tidak memiliki baris data.")

    for feature in FEATURES:
        dataframe[feature] = pd.to_numeric(dataframe[feature], errors="coerce")
    invalid = dataframe[FEATURES].isna().any(axis=1)
    if invalid.any():
        raise ValueError(
            f"Dataset memiliki {int(invalid.sum())} baris dengan fitur kosong "
            "atau bukan angka. Perbaiki dataset sebelum training."
        )
    if not np.isfinite(dataframe[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Dataset memiliki nilai fitur tak hingga; perbaiki sebelum training.")

    if "left" in dataframe.columns:
        dataframe["left"] = pd.to_numeric(dataframe["left"], errors="coerce")
        if dataframe["left"].isna().any():
            raise ValueError("Kolom 'left' berisi nilai kosong atau bukan angka.")
    return dataframe


def evaluate_clusters(
    scaled_features: np.ndarray,
) -> tuple[list[dict[str, float | int]], dict[int, KMeans]]:
    if len(scaled_features) <= max(EVALUATED_K):
        raise ValueError("Dataset harus memiliki lebih dari 8 baris untuk evaluasi K.")

    random = np.random.RandomState(RANDOM_STATE)
    sample_size = min(SILHOUETTE_SAMPLE_SIZE, len(scaled_features))
    sample_indices = random.choice(len(scaled_features), size=sample_size, replace=False)
    sample_features = scaled_features[sample_indices]
    evaluations: list[dict[str, float | int]] = []
    models: dict[int, KMeans] = {}

    for k in EVALUATED_K:
        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=10,
        )
        labels = model.fit_predict(scaled_features)
        sample_labels = labels[sample_indices]
        if len(np.unique(sample_labels)) < 2:
            raise ValueError(
                f"Sampel evaluasi tidak mencakup semua klaster untuk K={k}."
            )
        evaluations.append(
            {
                "k": k,
                "wcss": float(model.inertia_),
                "silhouette": float(
                    silhouette_score(sample_features, sample_labels)
                ),
                "dbi": float(davies_bouldin_score(scaled_features, labels)),
                "calinski_harabasz": float(
                    calinski_harabasz_score(scaled_features, labels)
                ),
            }
        )
        models[k] = model
    return evaluations, models


def assign_personas(means: pd.DataFrame) -> dict[int, str]:
    """Assign the four HR personas from cluster profiles, not label numbers."""
    if len(means) != OPTIMAL_K:
        raise ValueError(f"Persona assignment requires exactly {OPTIMAL_K} clusters.")

    remaining = set(int(cluster) for cluster in means.index)
    assigned: dict[int, str] = {}

    burnout_score = (
        means["average_montly_hours"].rank(pct=True)
        + means["number_project"].rank(pct=True)
        + (1 - means["satisfaction_level"].rank(pct=True))
    )
    burnout_cluster = int(burnout_score.idxmax())
    assigned[burnout_cluster] = "High Burnout"
    remaining.remove(burnout_cluster)

    remaining_clusters = sorted(remaining)
    veteran_score = 3 * means.loc[
        remaining_clusters, "time_spend_company"
    ].rank(pct=True)
    if "promotion_last_5years" in means.columns:
        veteran_score += 1 - means.loc[
            remaining_clusters, "promotion_last_5years"
        ].rank(pct=True)
    veteran_cluster = int(veteran_score.idxmax())
    assigned[veteran_cluster] = "Senior Veteran"
    remaining.remove(veteran_cluster)

    engagement_score = (
        means.loc[sorted(remaining), "satisfaction_level"].rank(pct=True)
        + means.loc[sorted(remaining), "last_evaluation"].rank(pct=True)
    )
    engaged_cluster = int(engagement_score.idxmax())
    assigned[engaged_cluster] = "Engaged Stars"
    remaining.remove(engaged_cluster)

    assigned[remaining.pop()] = "Disengaged"
    return assigned


def _risk_profiles(turnover_rates: dict[int, float]) -> dict[int, tuple[str, str]]:
    ordered = sorted(turnover_rates.items(), key=lambda item: (item[1], item[0]))
    levels = ("Rendah", "Sedang", "Tinggi", "Sangat Tinggi")
    output = {}
    for position, (cluster, _) in enumerate(ordered):
        level_index = min(position * len(levels) // len(ordered), len(levels) - 1)
        level = levels[level_index]
        output[cluster] = (level, RISK_COLORS[level])
    return output


def build_cluster_profiles(
    dataframe: pd.DataFrame,
    labels: np.ndarray,
) -> list[dict[str, Any]]:
    clustered = dataframe.copy()
    clustered["_cluster"] = labels
    means = clustered.groupby("_cluster")[FEATURES].mean()
    if "promotion_last_5years" in clustered.columns:
        means["promotion_last_5years"] = clustered.groupby("_cluster")[
            "promotion_last_5years"
        ].mean()
    personas = assign_personas(means)
    turnover_rates = (
        clustered.groupby("_cluster")["left"].mean().to_dict()
        if "left" in clustered.columns
        else {int(cluster): 0.0 for cluster in means.index}
    )
    risks = _risk_profiles(
        {int(cluster): float(rate) for cluster, rate in turnover_rates.items()}
    )

    profiles = []
    for cluster, row in means.iterrows():
        cluster_id = int(cluster)
        mask = labels == cluster_id
        risk_level, badge_color = risks[cluster_id]
        profiles.append(
            {
                "cluster": cluster_id,
                "persona": personas[cluster_id],
                "count": int(mask.sum()),
                "percentage": float(mask.mean() * 100),
                "means": {feature: float(row[feature]) for feature in FEATURES},
                "turnover_rate": float(turnover_rates[cluster_id]),
                "risk_level": risk_level,
                "badge_color": badge_color,
                "strategy": PERSONA_STRATEGIES[personas[cluster_id]],
            }
        )
    return profiles


def train_pipeline(
    dataset_path: Path = DATASET_PATH,
    artifacts_dir: Path = ARTIFACTS_DIR,
) -> dict[str, Any]:
    dataframe = load_training_data(dataset_path)
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(dataframe[FEATURES])
    evaluations, evaluated_models = evaluate_clusters(scaled_features)
    kmeans = evaluated_models[OPTIMAL_K]
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    pca.fit(scaled_features)
    profiles = build_cluster_profiles(dataframe, kmeans.labels_)
    profile_file = {
        "optimal_k": OPTIMAL_K,
        "evaluation": evaluations,
        "clusters": profiles,
        "training": {
            "dataset": dataset_path.name,
            "rows": int(len(dataframe)),
            "features": FEATURES,
            "random_state": RANDOM_STATE,
            "silhouette_sample_size": min(
                SILHOUETTE_SAMPLE_SIZE, len(dataframe)
            ),
            "duplicate_rows_retained": True,
            "scikit_learn_version": __import__("sklearn").__version__,
        },
    }

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, artifacts_dir / "scaler.joblib")
    joblib.dump(kmeans, artifacts_dir / "kmeans.joblib")
    joblib.dump(pca, artifacts_dir / "pca.joblib")
    with (artifacts_dir / "cluster_profiles.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(profile_file, file, ensure_ascii=False, indent=2)

    print(f"Dataset: {dataset_path} ({len(dataframe):,} baris)")
    print(f"K terpilih: {OPTIMAL_K} (ditetapkan PRD)")
    print(f"Artefak disimpan ke: {artifacts_dir}")
    print(pd.DataFrame(evaluations).to_string(index=False, float_format="%.4f"))
    print(
        pd.DataFrame(profiles)[
            [
                "cluster",
                "persona",
                "count",
                "percentage",
                "turnover_rate",
                "risk_level",
            ]
        ].to_string(index=False, float_format="%.3f")
    )
    return profile_file


if __name__ == "__main__":
    train_pipeline()
