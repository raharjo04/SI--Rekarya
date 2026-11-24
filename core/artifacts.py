import json
import re
from pathlib import Path

import joblib
import streamlit as st

from core.config import FEATURES, KMEANS_PATH, PCA_PATH, PROFILES_PATH, SCALER_PATH
from core.contracts import ArtifactBundle, ClusterProfiles


def _read_profiles(path: Path) -> ClusterProfiles:
    with path.open(encoding="utf-8") as file:
        profiles = json.load(file)
    if not isinstance(profiles, dict):
        raise ValueError(f"{path.name} harus berisi objek JSON.")
    if "optimal_k" not in profiles:
        raise ValueError(f"{path.name} wajib memiliki properti 'optimal_k'.")
    if "clusters" not in profiles or not isinstance(profiles["clusters"], list):
        raise ValueError(f"{path.name} wajib memiliki daftar 'clusters'.")
    if "evaluation" not in profiles or not isinstance(profiles["evaluation"], list):
        raise ValueError(f"{path.name} wajib memiliki daftar 'evaluation'.")

    required_cluster_fields = {
        "cluster",
        "persona",
        "count",
        "percentage",
        "means",
        "turnover_rate",
        "risk_level",
        "badge_color",
        "strategy",
    }
    for entry in profiles["clusters"]:
        if not isinstance(entry, dict) or not required_cluster_fields.issubset(entry):
            raise ValueError(
                "Setiap item 'clusters' harus memiliki cluster, persona, count, "
                "percentage, means, turnover_rate, risk_level, badge_color, dan strategy."
            )
        if not isinstance(entry["persona"], str) or not entry["persona"].strip():
            raise ValueError("Nama persona pada profil klaster tidak boleh kosong.")
        if not isinstance(entry["means"], dict):
            raise ValueError("'means' pada profil klaster harus berupa objek.")
        if not set(FEATURES).issubset(entry["means"]):
            raise ValueError(
                f"'means' pada setiap profil harus memuat fitur: {', '.join(FEATURES)}."
            )
        if not isinstance(entry["strategy"], list):
            raise ValueError("'strategy' pada profil klaster harus berupa daftar.")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(entry["badge_color"])):
            raise ValueError("'badge_color' harus berupa warna hex enam digit.")

    required_metrics = {
        "k",
        "wcss",
        "silhouette",
        "dbi",
        "calinski_harabasz",
    }
    if any(
        not isinstance(item, dict) or not required_metrics.issubset(item)
        for item in profiles["evaluation"]
    ):
        raise ValueError(
            "Setiap item 'evaluation' harus memiliki k, wcss, silhouette, dbi, "
            "dan calinski_harabasz."
        )
    evaluated_k = {int(item["k"]) for item in profiles["evaluation"]}
    if evaluated_k != set(range(2, 9)):
        raise ValueError("Evaluasi klaster harus mencakup semua nilai K dari 2 sampai 8.")
    return profiles


@st.cache_resource(show_spinner="Memuat model dan profil klaster...")
def load_artifacts() -> ArtifactBundle:
    """Load the pre-trained model assets once; never fit a model here."""
    paths = (SCALER_PATH, KMEANS_PATH, PCA_PATH, PROFILES_PATH)
    missing = [path for path in paths if not path.is_file()]
    if missing:
        missing_names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(
            f"Artefak belum ditemukan: {missing_names}. "
            "Jalankan `python train_pipeline.py` terlebih dahulu."
        )

    scaler = joblib.load(SCALER_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    pca = joblib.load(PCA_PATH)
    profiles = _read_profiles(PROFILES_PATH)

    optimal_k = int(profiles["optimal_k"])
    if int(kmeans.n_clusters) != optimal_k:
        raise ValueError(
            f"Jumlah klaster model ({kmeans.n_clusters}) tidak sama dengan "
            f"optimal_k di cluster_profiles.json ({optimal_k})."
        )
    if len(profiles["clusters"]) != optimal_k:
        raise ValueError(
            "Jumlah profil pada cluster_profiles.json harus sama dengan optimal_k."
        )
    cluster_ids = [int(profile["cluster"]) for profile in profiles["clusters"]]
    if sorted(cluster_ids) != list(range(optimal_k)):
        raise ValueError(
            "Label cluster pada profil harus unik dan mencakup 0 sampai optimal_k - 1."
        )
    if getattr(scaler, "n_features_in_", len(FEATURES)) != len(FEATURES):
        raise ValueError(
            f"Scaler harus menerima {len(FEATURES)} fitur dengan urutan {FEATURES}."
        )
    if getattr(kmeans, "n_features_in_", len(FEATURES)) != len(FEATURES):
        raise ValueError(
            f"K-Means harus menerima {len(FEATURES)} fitur dengan urutan {FEATURES}."
        )
    if getattr(pca, "n_features_in_", len(FEATURES)) != len(FEATURES):
        raise ValueError(
            f"PCA harus menerima {len(FEATURES)} fitur dengan urutan {FEATURES}."
        )
    if getattr(pca, "n_components_", 2) < 2:
        raise ValueError("PCA harus menyediakan minimal dua komponen untuk peta 2D.")

    return {
        "scaler": scaler,
        "kmeans": kmeans,
        "pca": pca,
        "profiles": profiles,
    }
