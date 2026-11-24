from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
DATA_DIR = ROOT_DIR / "data"
DATASET_NAME = "HR_comma_sep.csv"
DATASET_PATH = (
    DATA_DIR / DATASET_NAME
    if (DATA_DIR / DATASET_NAME).is_file()
    else ROOT_DIR / DATASET_NAME
)
SCALER_PATH = ARTIFACTS_DIR / "scaler.joblib"
KMEANS_PATH = ARTIFACTS_DIR / "kmeans.joblib"
PCA_PATH = ARTIFACTS_DIR / "pca.joblib"
PROFILES_PATH = ARTIFACTS_DIR / "cluster_profiles.json"

FEATURES = [
    "satisfaction_level",
    "last_evaluation",
    "number_project",
    "average_montly_hours",
    "time_spend_company",
]
INTEGER_FEATURES = {
    "number_project",
    "time_spend_company",
}
FEATURE_BOUNDS = {
    "satisfaction_level": (0.0, 1.0),
    "last_evaluation": (0.0, 1.0),
    "number_project": (2, 7),
    "average_montly_hours": (96, 310),
    "time_spend_company": (2, 10),
}
FEATURE_LABELS = {
    "satisfaction_level": "Tingkat kepuasan",
    "last_evaluation": "Evaluasi terakhir",
    "number_project": "Jumlah proyek",
    "average_montly_hours": "Jam kerja bulanan",
    "time_spend_company": "Masa kerja (tahun)",
}
BATCH_MAX_BYTES = 5 * 1024 * 1024
BATCH_MAX_ROWS = 20_000
