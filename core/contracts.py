from typing import NotRequired, TypedDict

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


class EmployeeInputBase(TypedDict):
    satisfaction_level: float
    last_evaluation: float
    number_project: int
    time_spend_company: int
    promotion_last_5years: NotRequired[bool]


class EmployeeInput(EmployeeInputBase):
    average_montly_hours: float


class EmployeeInputCorrectSpelling(EmployeeInputBase):
    average_monthly_hours: float


class FeatureValues(TypedDict):
    satisfaction_level: float
    last_evaluation: float
    number_project: float
    average_montly_hours: float
    time_spend_company: float


class ClusterEvaluation(TypedDict):
    k: int
    wcss: float
    silhouette: float
    dbi: float
    calinski_harabasz: float


class ClusterProfile(TypedDict):
    cluster: int
    persona: str
    count: int
    percentage: float
    means: FeatureValues
    turnover_rate: float
    risk_level: str
    badge_color: str
    strategy: list[str]


class TrainingMetadata(TypedDict):
    dataset: str
    rows: int
    features: list[str]
    random_state: int
    silhouette_sample_size: int
    duplicate_rows_retained: bool
    scikit_learn_version: str


class ClusterProfiles(TypedDict):
    optimal_k: int
    evaluation: list[ClusterEvaluation]
    clusters: list[ClusterProfile]
    training: NotRequired[TrainingMetadata]


class ArtifactBundle(TypedDict):
    scaler: StandardScaler
    kmeans: KMeans
    pca: PCA
    profiles: ClusterProfiles


class PredictionResult(TypedDict):
    cluster: int
    persona: str
    risk_level: str
    badge_color: str
    distance: float
    pca_x: float
    pca_y: float
    features: FeatureValues
    warnings: list[str]


class BatchPredictionResult(TypedDict):
    predictions: pd.DataFrame
    rejected: pd.DataFrame


class RecommendationResult(TypedDict):
    risk_level: str
    recommendations: list[str]
    triggered_rules: list[str]
    policy_note: str


class SummaryStats(TypedDict):
    total_karyawan: int
    turnover_rate: float
    rata_kepuasan: float
    rata_jam_bulanan: float
    scatter_sample: pd.DataFrame
    project_summary: pd.DataFrame


ValidateInputResult = tuple[pd.DataFrame, list[str]]
PredictorInput = EmployeeInput | EmployeeInputCorrectSpelling
