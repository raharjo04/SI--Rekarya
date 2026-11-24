import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from core import artifacts as artifact_module
from core import recommender as recommender_module
from core.charts import (
    cluster_distribution,
    cluster_map,
    evaluation_charts,
    project_turnover,
    summary_scatter,
)
from core.config import FEATURES
from core.data import summary_stats
from core.predictor import predict_batch, predict_one
from core.recommender import recommend
from train_pipeline import assign_personas


@pytest.fixture
def fitted_artifacts():
    random = np.random.RandomState(42)
    centers = np.array(
        [
            [0.2, 0.3, 2, 120, 2],
            [0.4, 0.5, 4, 160, 4],
            [0.7, 0.8, 5, 210, 6],
            [0.9, 0.9, 7, 280, 9],
        ],
        dtype=float,
    )
    values = np.vstack(
        [
            center
            + random.normal(
                0,
                [0.015, 0.015, 0.15, 5, 0.15],
                size=(40, len(FEATURES)),
            )
            for center in centers
        ]
    )
    frame = pd.DataFrame(values, columns=FEATURES)
    scaler = StandardScaler().fit(frame)
    scaled = scaler.transform(frame)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10).fit(scaled)
    pca = PCA(n_components=2, random_state=42).fit(scaled)
    return {
        "scaler": scaler,
        "kmeans": kmeans,
        "pca": pca,
        "profiles": _profiles(),
    }


def _profiles():
    evaluation = [
        {
            "k": k,
            "wcss": float(10 - k),
            "silhouette": 0.4,
            "dbi": 0.8,
            "calinski_harabasz": 100.0,
        }
        for k in range(2, 9)
    ]
    return {
        "optimal_k": 4,
        "evaluation": evaluation,
        "clusters": [
            {
                "cluster": index,
                "persona": f"Persona {index}",
                "count": 10,
                "percentage": 25.0,
                "means": {feature: 0.0 for feature in FEATURES},
                "turnover_rate": 0.1,
                "risk_level": "Sedang",
                "badge_color": "#0D9488",
                "strategy": [],
            }
            for index in range(4)
        ],
    }


def test_load_artifacts_validates_optimal_cluster_count(tmp_path, monkeypatch):
    scaler = StandardScaler().fit(pd.DataFrame(np.random.RandomState(4).rand(40, 5), columns=FEATURES))
    scaled = scaler.transform(pd.DataFrame(np.random.RandomState(5).rand(40, 5), columns=FEATURES))
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10).fit(scaled)
    pca = PCA(n_components=2, random_state=42).fit(scaled)
    paths = {
        "SCALER_PATH": tmp_path / "scaler.joblib",
        "KMEANS_PATH": tmp_path / "kmeans.joblib",
        "PCA_PATH": tmp_path / "pca.joblib",
        "PROFILES_PATH": tmp_path / "cluster_profiles.json",
    }
    for key, model in (("SCALER_PATH", scaler), ("KMEANS_PATH", kmeans), ("PCA_PATH", pca)):
        joblib.dump(model, paths[key])
    paths["PROFILES_PATH"].write_text(json.dumps(_profiles()), encoding="utf-8")
    for key, path in paths.items():
        monkeypatch.setattr(artifact_module, key, path)

    artifact_module.load_artifacts.clear()
    try:
        loaded = artifact_module.load_artifacts()
    finally:
        artifact_module.load_artifacts.clear()
    assert loaded["kmeans"].n_clusters == loaded["profiles"]["optimal_k"]


def test_batch_matches_individual_predictions(fitted_artifacts):
    records = pd.DataFrame(
        [
            {
                "satisfaction_level": 0.2 + index % 4 * 0.2,
                "last_evaluation": 0.3 + index % 4 * 0.15,
                "number_project": 2 + index % 6,
                "average_montly_hours": 120 + index % 180,
                "time_spend_company": 2 + index % 9,
            }
            for index in range(50)
        ]
    )
    batch = predict_batch(records, fitted_artifacts)["predictions"]
    individual = [
        predict_one(record, fitted_artifacts)["cluster"]
        for record in records.to_dict(orient="records")
    ]
    assert batch["Cluster"].tolist() == individual
    for index, cluster in enumerate(individual):
        profile = fitted_artifacts["profiles"]["clusters"][cluster]
        prediction = predict_one(records.iloc[index].to_dict(), fitted_artifacts)
        assert batch.iloc[index]["Persona"] == profile["persona"]
        assert batch.iloc[index]["Risk_Level"] == profile["risk_level"]
        assert batch.iloc[index]["badge_color"] == profile["badge_color"]
        assert prediction["persona"] == profile["persona"]
        assert prediction["risk_level"] == profile["risk_level"]
        assert prediction["badge_color"] == profile["badge_color"]


def test_batch_rejects_bad_row_but_processes_valid_rows(fitted_artifacts):
    records = pd.DataFrame(
        [
            {
                "satisfaction_level": 0.5,
                "last_evaluation": 0.7,
                "number_project": 4,
                "average_montly_hours": 160,
                "time_spend_company": 3,
            },
            {
                "satisfaction_level": 1.5,
                "last_evaluation": 0.7,
                "number_project": 4,
                "average_montly_hours": 160,
                "time_spend_company": 3,
            },
        ]
    )
    result = predict_batch(records, fitted_artifacts)
    assert len(result["predictions"]) == 1
    assert len(result["rejected"]) == 1
    assert "satisfaction_level" in result["rejected"].iloc[0]["Alasan"]


def test_batch_rejects_empty_and_non_integer_features(fitted_artifacts):
    records = pd.DataFrame(
        [
            {
                "satisfaction_level": None,
                "last_evaluation": 0.7,
                "number_project": 4,
                "average_montly_hours": 160,
                "time_spend_company": 3,
            },
            {
                "satisfaction_level": 0.5,
                "last_evaluation": 0.7,
                "number_project": 4.5,
                "average_montly_hours": 160,
                "time_spend_company": 3,
            },
            {
                "satisfaction_level": 0.5,
                "last_evaluation": 0.7,
                "number_project": 4,
                "average_montly_hours": 160,
                "time_spend_company": 3,
            },
        ]
    )
    result = predict_batch(records, fitted_artifacts)
    assert len(result["predictions"]) == 1
    assert len(result["rejected"]) == 2
    assert result["rejected"]["Alasan"].str.contains(
        "harus berupa bilangan bulat|harus berisi angka"
    ).all()


def test_batch_accepts_correct_monthly_hours_spelling(fitted_artifacts):
    records = pd.DataFrame(
        [
            {
                "satisfaction_level": 0.5,
                "last_evaluation": 0.7,
                "number_project": 4,
                "average_monthly_hours": 160,
                "time_spend_company": 3,
            }
        ]
    )
    result = predict_batch(records, fitted_artifacts)
    assert len(result["predictions"]) == 1
    assert result["rejected"].empty
    assert "average_monthly_hours" in result["predictions"].columns
    assert "average_montly_hours" not in result["predictions"].columns


def test_missing_feature_column_is_reported(fitted_artifacts):
    with pytest.raises(ValueError, match="time_spend_company"):
        predict_batch(
            pd.DataFrame(
                [
                    {
                        "satisfaction_level": 0.5,
                        "last_evaluation": 0.7,
                        "number_project": 4,
                        "average_montly_hours": 160,
                    }
                ]
            ),
            fitted_artifacts,
        )


@pytest.mark.parametrize(
    ("persona", "data", "expected_rule"),
    [
        (
            "High Burnout",
            {"average_montly_hours": 251, "number_project": 5},
            "R1",
        ),
        ("Disengaged", {"last_evaluation": 0.59}, "R2"),
        ("Engaged Stars", {"last_evaluation": 0.80}, "R3"),
        (
            "Senior Veteran",
            {"promotion_last_5years": False},
            "R4",
        ),
        ("Persona lain", {"satisfaction_level": 0.349}, "R5"),
    ],
)
def test_recommendation_rules(persona, data, expected_rule):
    complete_data = {
        "average_montly_hours": 160,
        "number_project": 4,
        "last_evaluation": 0.7,
        "satisfaction_level": 0.5,
    }
    complete_data.update(data)
    result = recommend(persona, complete_data, risk_level="Sedang")
    assert expected_rule in result["triggered_rules"]
    assert result["risk_level"] == "Sedang"


def test_training_personas_follow_cluster_profiles_not_cluster_ids():
    means = pd.DataFrame(
        [
            [0.48, 0.55, 2.7, 153, 3.1, 0.02],
            [0.17, 0.81, 5.6, 248, 4.3, 0.01],
            [0.75, 0.82, 4.2, 222, 6.2, 0.04],
            [0.75, 0.75, 3.8, 209, 2.8, 0.02],
        ],
        index=[2, 0, 3, 1],
        columns=FEATURES + ["promotion_last_5years"],
    )
    personas = assign_personas(means)
    assert personas == {
        0: "High Burnout",
        3: "Senior Veteran",
        1: "Engaged Stars",
        2: "Disengaged",
    }


def test_senior_veteran_rule_waits_for_optional_promotion_value():
    result = recommend(
        "Senior Veteran",
        {
            "average_montly_hours": 160,
            "number_project": 4,
            "last_evaluation": 0.7,
            "satisfaction_level": 0.5,
        },
    )
    assert "R4" not in result["triggered_rules"]


def test_recommend_resolves_risk_from_persona_profile(monkeypatch):
    monkeypatch.setattr(
        recommender_module,
        "load_artifacts",
        lambda: {
            "profiles": {
                "clusters": [
                    {"persona": "High Burnout", "risk_level": "Sangat Tinggi"}
                ]
            }
        },
    )
    result = recommend(
        "High Burnout",
        {
            "average_montly_hours": 160,
            "number_project": 4,
            "last_evaluation": 0.7,
            "satisfaction_level": 0.5,
        },
    )
    assert result["risk_level"] == "Sangat Tinggi"


def test_summary_stats_calculates_kpis_aggregates_and_fixed_sample():
    dataframe = pd.DataFrame(
        {
            "left": [0, 1, 0, 1] * 751,
            "satisfaction_level": [0.2, 0.4, 0.6, 0.8] * 751,
            "average_montly_hours": [120, 140, 160, 180] * 751,
            "number_project": [2, 2, 3, 3] * 751,
        }
    )
    stats = summary_stats(dataframe)
    assert stats["total_karyawan"] == len(dataframe) == 3004
    assert stats["turnover_rate"] == pytest.approx(0.5)
    assert stats["rata_kepuasan"] == pytest.approx(0.5)
    assert stats["rata_jam_bulanan"] == pytest.approx(150)
    assert len(stats["scatter_sample"]) == 3000
    pd.testing.assert_frame_equal(
        stats["scatter_sample"],
        dataframe.sample(n=3000, random_state=42),
    )
    assert stats["project_summary"].to_dict(orient="records") == [
        {"jumlah_proyek": 2, "jumlah_karyawan": 1502, "turnover_rate": 0.5},
        {"jumlah_proyek": 3, "jumlah_karyawan": 1502, "turnover_rate": 0.5},
    ]


def test_cluster_charts_use_profile_colors_and_pca_variance(fitted_artifacts):
    profile_rows = _profiles()["clusters"]
    prediction_rows = pd.DataFrame(
        {
            "Cluster": [0, 1, 1],
            "Persona": ["Persona 0", "Persona 1", "Persona 1"],
            "badge_color": ["#112233", "#445566", "#445566"],
        }
    )
    distribution = cluster_distribution(prediction_rows)
    colors = set(distribution.data[0].marker.colors)
    assert colors == {"#112233", "#445566"}
    assert sum(distribution.data[0].values) == 3
    assert distribution.data[0].hole == 0.58

    sample = pd.DataFrame(
        [
            [0.2, 0.3, 2, 120, 2],
            [0.9, 0.9, 7, 280, 9],
        ],
        columns=FEATURES,
    )
    scaled = fitted_artifacts["scaler"].transform(sample[FEATURES])
    coordinates = fitted_artifacts["pca"].transform(scaled)
    points = pd.DataFrame(
        {
            "PCA1": coordinates[:, 0],
            "PCA2": coordinates[:, 1],
            "Cluster": fitted_artifacts["kmeans"].predict(scaled),
        }
    )
    pca_figure = cluster_map(
        points,
        profile_rows,
        fitted_artifacts["pca"],
        fitted_artifacts["kmeans"],
    )
    assert "varians" in pca_figure.layout.xaxis.title.text
    assert "varians" in pca_figure.layout.yaxis.title.text


def test_summary_and_evaluation_charts_build_figures():
    sample = pd.DataFrame(
        {
            "average_montly_hours": [120, 220],
            "satisfaction_level": [0.3, 0.8],
            "left": [1, 0],
        }
    )
    project_summary = pd.DataFrame(
        {
            "jumlah_proyek": [2, 3],
            "jumlah_karyawan": [10, 20],
            "turnover_rate": [0.2, 0.1],
        }
    )
    evaluation = pd.DataFrame(
        {
            "k": [2, 3, 4],
            "wcss": [100.0, 70.0, 55.0],
            "silhouette": [0.3, 0.4, 0.35],
        }
    )
    assert len(summary_scatter(sample).data) == 2
    assert len(project_turnover(project_summary).data) == 2
    assert len(evaluation_charts(evaluation, optimal_k=3).data) == 2
