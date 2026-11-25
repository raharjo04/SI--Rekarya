import asyncio
import re
from typing import Any

import httpx
import pandas as pd

from core.data import load_dataset
from webapp.downloads import DownloadStore
from webapp.main import app
from webapp.routes import audit as audit_module
from webapp.services import (
    build_high_load_metrics,
    build_persona_cards,
    build_workload_bubbles,
)


class ASGITestClient:
    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async def send_request() -> httpx.Response:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send_request())

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)


client = ASGITestClient()


def test_dashboard_pages_render_with_expected_content():
    summary = client.get("/")
    personas = client.get("/personas")
    detection = client.get("/detect")
    audit = client.get("/audit")

    assert summary.status_code == 200
    assert "Temuan utama" in summary.text
    assert "Persentase karyawan yang pernah keluar" in summary.text
    assert "workload-bubbles" in summary.text
    assert "Rata-rata seluruh data" in summary.text
    assert personas.status_code == 200
    assert personas.text.count('class="card persona-card"') == 4
    assert "Detail teknis" in personas.text
    assert detection.status_code == 200
    assert 'hx-post="/detect"' in detection.text
    assert audit.status_code == 200
    assert "Unduh template CSV" in audit.text
    assert "average_monthly_hours" in audit.text
    assert client.get("/health").json() == {"status": "ok"}


def test_workload_bubbles_show_exit_rate_with_group_size():
    dataframe = pd.DataFrame(
        {
            "average_montly_hours": [255, 258, 245, 165],
            "satisfaction_level": [0.25, 0.26, 0.25, 0.55],
            "left": [1, 0, 1, 0],
        }
    )

    chart = build_workload_bubbles(dataframe)
    bubble = next(
        point
        for point in chart["points"]
        if point["hourRange"] == "240–260 jam"
        and point["satisfactionRange"] == "0,2–0,3"
    )
    high_load = build_high_load_metrics(dataframe)

    assert chart["total_count"] == 4
    assert bubble["count"] == 3
    assert bubble["exits"] == 2
    assert abs(bubble["exitRate"] - (200 / 3)) < 1e-9
    assert bubble["color"] == "#B91C1C"
    assert high_load == {"count": 2, "exit_rate": 50.0}


def test_persona_cards_compare_historical_turnover_to_overall_rate():
    profile = {
        "cluster": 0,
        "persona": "Persona Contoh",
        "count": 20,
        "percentage": 20.0,
        "means": {
            "satisfaction_level": 0.3,
            "average_montly_hours": 200,
            "number_project": 4,
        },
        "turnover_rate": 0.5,
        "risk_level": "Tinggi",
        "badge_color": "#b91c1c",
        "strategy": [],
    }

    card = build_persona_cards([profile], overall_turnover=23.8)[0]

    assert card["turnover_percent"] == 50.0
    assert (
        "26,2 poin persentase di atas rata-rata keseluruhan (23,8%)"
        in card["benchmark_note"]
    )


def test_detection_returns_group_explanation_recommendations_and_comparison():
    response = client.post(
        "/detect",
        data={
            "satisfaction_level": "0.17",
            "last_evaluation": "0.81",
            "number_project": "6",
            "average_montly_hours": "258",
            "time_spend_company": "5",
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert "High Burnout" in response.text
    assert "Dari 100 karyawan serupa" in response.text
    assert "Rekomendasi HR" in response.text
    assert "Perbandingan" in response.text
    assert "Jarak ke pusat kelompok" in response.text
    assert "<!doctype html>" not in response.text.lower()


def test_detection_rejects_out_of_range_input():
    response = client.post(
        "/detect",
        data={
            "satisfaction_level": "1.5",
            "last_evaluation": "0.81",
            "number_project": "6",
            "average_montly_hours": "258",
            "time_spend_company": "5",
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 422
    assert "satisfaction_level harus berada" in response.text


def test_audit_processes_valid_rows_and_downloads_temporary_csv():
    csv_content = (
        "satisfaction_level,last_evaluation,number_project,"
        "average_monthly_hours,time_spend_company\n"
        "0.5,0.7,4,160,3\n"
        "1.5,0.7,4,160,3\n"
    )
    response = client.post(
        "/audit",
        files={"file": ("sample.csv", csv_content.encode("utf-8"), "text/csv")},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert "Berhasil diproses" in response.text
    assert "Ditolak" in response.text
    assert "satisfaction_level harus berada" in response.text
    match = re.search(r'href="([^"]*/audit/download/[^"]+)"', response.text)
    assert match is not None

    download = client.get(match.group(1))
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("text/csv")
    assert b"Persona" in download.content
    assert client.get(match.group(1)).status_code == 200


def test_audit_rejects_uploads_over_size_and_row_limits(monkeypatch):
    monkeypatch.setattr(audit_module, "BATCH_MAX_BYTES", 10)
    oversized = client.post(
        "/audit",
        files={"file": ("large.csv", b"a" * 11, "text/csv")},
    )
    assert oversized.status_code == 413
    assert "5 MB" in oversized.text

    monkeypatch.setattr(audit_module, "BATCH_MAX_BYTES", 5 * 1024 * 1024)
    monkeypatch.setattr(audit_module, "BATCH_MAX_ROWS", 1)
    csv_content = (
        "satisfaction_level,last_evaluation,number_project,"
        "average_montly_hours,time_spend_company\n"
        "0.5,0.7,4,160,3\n"
        "0.6,0.8,5,170,4\n"
    )
    too_many_rows = client.post(
        "/audit",
        files={"file": ("rows.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert too_many_rows.status_code == 413
    assert "20.000 baris" in too_many_rows.text


def test_audit_template_download_and_download_token_expiry():
    template = client.get("/audit/template.csv")
    assert template.status_code == 200
    assert b"average_montly_hours" in template.content

    store = DownloadStore(ttl_seconds=0)
    token = store.create(b"hasil")
    assert store.get(token) is None


def test_dataset_loader_returns_independent_dataframes(tmp_path):
    dataset_path = tmp_path / "sample.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset_path, index=False)

    first = load_dataset(dataset_path)
    first.loc[0, "value"] = 2
    second = load_dataset(dataset_path)

    assert second.loc[0, "value"] == 1
