from functools import lru_cache
from pathlib import Path

import pandas as pd

from core.config import DATASET_PATH
from core.contracts import SummaryStats


@lru_cache(maxsize=2)
def _read_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {path.name}. "
            "Letakkan HR_comma_sep.csv di root proyek atau folder data/, lalu "
            "jalankan `python train_pipeline.py` untuk menyiapkan model."
        )
    return pd.read_csv(path)


def load_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    return _read_dataset(path).copy(deep=True)


def summary_stats(dataframe: pd.DataFrame) -> SummaryStats:
    required = {
        "left",
        "satisfaction_level",
        "average_montly_hours",
        "number_project",
    }
    missing = sorted(required.difference(dataframe.columns))
    if missing:
        raise ValueError(f"Kolom dataset tidak tersedia: {', '.join(missing)}.")
    if dataframe.empty:
        raise ValueError("Dataset tidak memiliki baris data.")

    left = pd.to_numeric(dataframe["left"], errors="coerce")
    satisfaction = pd.to_numeric(
        dataframe["satisfaction_level"], errors="coerce"
    )
    monthly_hours = pd.to_numeric(
        dataframe["average_montly_hours"], errors="coerce"
    )
    project_summary = (
        dataframe.assign(
            _left=left,
            _project=pd.to_numeric(dataframe["number_project"], errors="coerce"),
        )
        .dropna(subset=["_left", "_project"])
        .groupby("_project", as_index=False)
        .agg(
            jumlah_karyawan=("_left", "size"),
            turnover_rate=("_left", "mean"),
        )
        .rename(columns={"_project": "jumlah_proyek"})
        .sort_values("jumlah_proyek")
    )
    sample = dataframe.sample(
        n=min(3000, len(dataframe)), random_state=42
    ).copy()
    return {
        "total_karyawan": int(len(dataframe)),
        "turnover_rate": float(left.mean()),
        "rata_kepuasan": float(satisfaction.mean()),
        "rata_jam_bulanan": float(monthly_hours.mean()),
        "scatter_sample": sample,
        "project_summary": project_summary,
    }
