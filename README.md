# SI-REKARYA

Aplikasi analitik SDM berbasis Streamlit yang memuat model K-Means hasil
pelatihan offline. Aplikasi tidak melatih ulang model dan tidak menggunakan
REST API atau database.

## Cara menjalankan (Windows)

Buka folder proyek yang berisi `app.py` di VS Code, lalu pilih **Terminal >
New Terminal**. Jalankan langkah-langkah berikut di terminal itu.

1. Pastikan Python 3.11 tersedia:

   ```powershell
   py -3.11 --version
   ```

2. Letakkan `HR_comma_sep.csv` di folder `data\` atau di root proyek.

3. Buat lingkungan Python proyek (lewati jika `.venv` sudah ada):

   ```powershell
   py -3.11 -m venv .venv
   ```

4. Pasang kebutuhan aplikasi:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Siapkan model (pertama kali atau setelah dataset diganti):

   ```powershell
   .\.venv\Scripts\python.exe train_pipeline.py
   ```

6. Jalankan aplikasi:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py
   ```

7. Buka alamat yang muncul, biasanya `http://localhost:8501`. Untuk berhenti,
   kembali ke terminal lalu tekan **Ctrl+C**.

Pipeline memakai `HR_comma_sep.csv` yang tersedia di root atau folder `data/`.
Model K-Means dilatih offline dengan K=4; metrik evaluasi K=2 sampai K=8
disimpan bersama profil persona.

## Susunan artefak

`core.artifacts.load_artifacts()` memuat empat file berikut satu kali dan tidak
pernah menjalankan `fit`:

- `artifacts/scaler.joblib`
- `artifacts/kmeans.joblib`
- `artifacts/pca.joblib`
- `artifacts/cluster_profiles.json`

Urutan kolom scaler, K-Means, dan PCA harus sama dengan
`core.config.FEATURES`: `satisfaction_level`, `last_evaluation`,
`number_project`, `average_montly_hours`, `time_spend_company`. Scaler dipakai
dengan `transform()` untuk seluruh prediksi.

`cluster_profiles.json` menggunakan bentuk berikut; `evaluation` berisi satu
rekaman untuk setiap K dari 2 sampai 8, sedangkan `clusters` berisi satu profil
untuk setiap label model:

```json
{
  "optimal_k": 4,
  "evaluation": [
    {
      "k": 2,
      "wcss": 0.0,
      "silhouette": 0.0,
      "dbi": 0.0,
      "calinski_harabasz": 0.0
    }
  ],
  "clusters": [
    {
      "cluster": 0,
      "persona": "High Burnout",
      "count": 100,
      "percentage": 10.0,
      "means": {
        "satisfaction_level": 0.0,
        "last_evaluation": 0.0,
        "number_project": 0.0,
        "average_montly_hours": 0.0,
        "time_spend_company": 0.0
      },
      "turnover_rate": 0.0,
      "risk_level": "Tinggi",
      "badge_color": "#DC2626",
      "strategy": ["Contoh strategi HR"]
    }
  ]
}
```

Nilai `percentage` dan `turnover_rate` dinyatakan dalam skala 0–100 dan 0–1
secara berurutan. Properti `means` memakai nama fitur model. Isi persona,
tingkat risiko, warna, evaluasi, jumlah, dan strategi harus berasal dari
training proyek; jangan menyalin angka contoh di atas.

## Prediksi dan validasi CSV

Rentang validasi mengikuti widget demo: kepuasan dan evaluasi 0–1, jumlah
proyek 2–7, jam kerja bulanan 96–310, serta masa kerja 2–10 tahun. Prediksi
batch mempertahankan baris yang valid dan melaporkan baris yang ditolak.
Kolom `average_monthly_hours` diterima sebagai alias ejaan yang benar bagi
`average_montly_hours`.

Hasil `predict_one()` memuat label klaster, jarak centroid dalam ruang scaled,
koordinat PCA, fitur yang telah dibersihkan, dan peringatan. `predict_batch()`
mengembalikan `{"predictions": DataFrame, "rejected": DataFrame}`.
Rekomendasi R1–R5 adalah heuristik kebijakan HR, bukan keluaran model.

## Kontrak internal `core/`

Struktur tipe bersama ada di `core/contracts.py`. Kontrak fungsi untuk halaman:

| Fungsi | Input | Return |
| --- | --- | --- |
| `load_artifacts()` | — | `ArtifactBundle`: `scaler`, `kmeans`, `pca`, `profiles` |
| `validate_input(data)` | `PredictorInput` | `ValidateInputResult`: `(DataFrame[FEATURES], warnings)` |
| `predict_one(data, artifacts=None)` | `PredictorInput`, artefak opsional | `PredictionResult`: `cluster`, `persona`, `risk_level`, `badge_color`, `distance`, `pca_x`, `pca_y`, `features`, `warnings` |
| `predict_batch(df, artifacts=None)` | `DataFrame`, artefak opsional | `BatchPredictionResult`: `predictions`, `rejected` |
| `recommend(persona, data, risk_level=None)` | nama persona, data fitur, tingkat risiko opsional | `RecommendationResult`: `risk_level`, `recommendations`, `triggered_rules`, `policy_note` |
| `summary_stats(df)` | dataset SDM | `SummaryStats`: KPI, `scatter_sample`, `project_summary` |

`predict_batch()` mempertahankan kolom masukan asli pada kedua DataFrame hasil.
`predictions` juga memuat `Cluster`, `Persona`, `Risk_Level`, `badge_color`,
`Jarak centroid`, `PCA1`, `PCA2`, dan `Peringatan`; `rejected` memuat
`Nomor baris` dan `Alasan`. Persona, tingkat risiko, dan warna diambil dari
profil JSON berdasarkan label hasil model. Kolom fitur wajib yang hilang
menggagalkan validasi file, sedangkan nilai baris yang tidak valid dilaporkan
terpisah. Alias `average_monthly_hours` diterima tanpa mengubah nama kolom asli
pada tabel hasil.

## Tes

Jalankan tes core dari root proyek setelah dependensi terpasang:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Versi pandas, NumPy, scikit-learn, dan joblib dipatok agar sama dengan
lingkungan training yang menghasilkan artefak yang ada di proyek ini.
