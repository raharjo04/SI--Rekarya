# PRD SI-REKARYA (Aplikasi Streamlit)

Nov 24, 2026 · @raharjo

SI-REKARYA dibangun sebagai **satu aplikasi Streamlit**: tampilan dan logika dalam satu proyek Python yang memuat model K-Means hasil `train_pipeline.py`, tanpa REST API, tanpa database, dan tanpa frontend terpisah. Presentasi: Kamis, 26 November 2026.

## 1. Ringkasan

Aplikasi memuat artefak `.joblib` dan `cluster_profiles.json` sekali saat start, lalu menyajikan empat halaman: Ringkasan SDM, Peta Klaster, Deteksi Karyawan, dan Audit Data Massal. Model **tidak dilatih ulang** di aplikasi; pelatihan tetap offline lewat `train_pipeline.py`.

Pemisahan "backend" tetap dijaga di level kode: semua logika ada di folder `core/`, sedangkan halaman Streamlit hanya memanggil fungsinya dan menampilkan hasil.

## 2. Tujuan dan Non-Tujuan

### Tujuan

- Mengubah hasil K-Means (K=4) menjadi aplikasi interaktif yang bisa didemokan langsung di depan dosen.
- Prediksi satu karyawan dan prediksi massal memakai scaler dan urutan fitur yang sama dengan training.
- Menampilkan bukti pemilihan K, peta PCA 2D, dan profil tiap klaster.
- Menghasilkan rekomendasi HR berbasis aturan untuk setiap hasil prediksi.

### Non-Tujuan

- Tidak ada login atau akun, database, maupun retraining dari aplikasi.
- Tidak ada REST API dan tidak ada deployment produksi.

## 3. Perubahan dari Rencana FastAPI

| Aspek | Rencana FastAPI | Rencana Streamlit |
| --- | --- | --- |
| Arsitektur | API dan frontend terpisah | Satu aplikasi Python |
| Komunikasi | Request/response JSON | Pemanggilan fungsi langsung |
| Validasi input | Pydantic | Widget Streamlit + fungsi `validate_input()` |
| Tampilan | HTML/React | Halaman di folder `pages/` |
| Dokumentasi | Swagger `/docs` | README + halaman aplikasi itu sendiri |
| Menjalankan | Uvicorn + server frontend | `streamlit run app.py` |

Yang tidak dipakai lagi: FastAPI, Uvicorn, Pydantic, python-multipart, CORS, dan kontrak JSON antar-tim.

## 4. Tech Stack

| Komponen | Pilihan | Catatan |
| --- | --- | --- |
| Bahasa | Python 3.11 | Samakan dengan environment training |
| UI dan state | Streamlit | Form, upload/download CSV, `st.session_state`, cache |
| Data | pandas, numpy | Dataset dan agregat EDA |
| ML | scikit-learn, joblib | **Versi scikit-learn harus sama dengan saat training** |
| Grafik | Plotly (`st.plotly_chart`) | Interaktif, warna mengikuti `badge_color` |
| Test | pytest | Hanya menguji `core/`, tanpa UI |

Pin semua versi di `requirements.txt` dari `pip freeze` mesin yang menjalankan training.

## 5. Arsitektur dan Struktur Folder

```
si-rekarya/
├── app.py                  # entry point: konfigurasi halaman, header, tema
├── pages/
│   ├── 1_Ringkasan_SDM.py
│   ├── 2_Peta_Klaster.py
│   ├── 3_Deteksi_Karyawan.py
│   └── 4_Audit_Data_Massal.py
├── core/                   # "backend": logika tanpa kode tampilan
│   ├── config.py           # path, daftar fitur, batas validasi
│   ├── artifacts.py        # load scaler, kmeans, pca, profiles
│   ├── data.py             # load dataset + agregat EDA
│   ├── predictor.py        # validasi, transform, predict, jarak, PCA
│   ├── recommender.py      # aturan risiko dan rekomendasi (R1-R5)
│   └── charts.py           # fungsi pembuat figure Plotly
├── artifacts/              # hasil train_pipeline.py (4 file)
├── data/HR_comma_sep.csv
├── .streamlit/config.toml  # tema navy/teal
├── tests/
├── requirements.txt
└── README.md
```

Streamlit menjalankan ulang skrip setiap ada interaksi, jadi pemuatan berat dibungkus cache: `@st.cache_resource` untuk model dan `@st.cache_data` untuk dataset serta agregat. Dekorator cache adalah satu-satunya kode Streamlit yang boleh ada di `core/`; selebihnya Python murni agar bisa dites dengan pytest.

## 6. Spesifikasi Halaman

### 6.1 Ringkasan SDM

- Empat kartu `st.metric`: total karyawan, turnover rate, rata-rata kepuasan, rata-rata jam kerja bulanan.
- Scatter jam kerja vs kepuasan, diwarnai status `left` (sampel acak maksimal 3.000 titik, seed tetap).
- Bar distribusi jumlah proyek beserta turnover rate per jumlah proyek.
- Semua angka dihitung dari dataset, bukan diketik manual.

### 6.2 Peta Klaster

- Tabel evaluasi K=2..8 (WCSS, Silhouette, DBI, Calinski-Harabasz) dari `cluster_profiles.json`, dengan K terpilih ditandai.
- Grafik Elbow dan Silhouette berdampingan.
- Scatter PCA 2D dengan warna per klaster dan posisi centroid; sumbu memuat persen varians.
- Tabel profil klaster: persona, jumlah dan persen karyawan, rata-rata fitur asli, turnover rate, tingkat risiko.
- Expander per klaster berisi strategi HR. Radar chart bersifat opsional (kerjakan terakhir).

### 6.3 Deteksi Karyawan (fitur utama demo)

| Input | Widget | Rentang |
| --- | --- | --- |
| Tingkat kepuasan | Slider | 0,00 - 1,00 |
| Evaluasi terakhir | Slider | 0,00 - 1,00 |
| Jumlah proyek | Slider | 2 - 7 |
| Jam kerja bulanan | Slider | 96 - 310 |
| Masa kerja (tahun) | Slider | 2 - 10 |
| Promosi 5 tahun terakhir | Checkbox | Ya / tidak (dipakai aturan R4) |

Semua widget berada dalam `st.form`, sehingga analisis baru berjalan saat tombol **Analisis** ditekan. Hasil yang ditampilkan:

- Persona dan nomor klaster dengan badge warna sesuai tingkat risiko.
- Tingkat risiko dan turnover rate historis klaster tersebut.
- Jarak ke centroid (ruang ter-scaling).
- Titik karyawan pada scatter PCA bersama klaster lain.
- Daftar rekomendasi HR, dan kode aturan yang terpicu (R1-R5).

Hasil terakhir disimpan di `st.session_state` agar tidak hilang saat halaman dirender ulang.

### 6.4 Audit Data Massal

- `st.file_uploader` untuk CSV, plus tombol unduh template CSV berisi lima kolom fitur.
- Kolom wajib: lima fitur model. `average_monthly_hours` (ejaan benar) diterima dan dipetakan ke `average_montly_hours`.
- Batas: 5 MB dan 20.000 baris. Baris tidak valid tidak menggagalkan seluruh file; baris itu dilaporkan dalam tabel terpisah.
- Tampilkan ringkasan (baris diproses, baris ditolak), grafik distribusi klaster, dan pratinjau tabel hasil.
- Tombol `st.download_button` mengunduh CSV hasil: data asli + kolom `Cluster`, `Persona`, `Risk_Level`, `Rekomendasi_HR`.

## 7. Logika Inti (`core/`)

| Fungsi | Modul | Tugas |
| --- | --- | --- |
| `load_artifacts()` | `artifacts.py` | Memuat scaler, kmeans, pca, dan profil klaster (di-cache) |
| `validate_input(data)` | `predictor.py` | Cek rentang, kembalikan data bersih dan daftar `warnings` |
| `predict_one(data)` | `predictor.py` | Scale, prediksi klaster, jarak ke centroid, posisi PCA |
| `predict_batch(df)` | `predictor.py` | Prediksi vektor untuk seluruh baris, pisahkan baris tidak valid |
| `recommend(persona, data)` | `recommender.py` | Tingkat risiko, rekomendasi, dan kode aturan terpicu |
| `summary_stats()` | `data.py` | KPI dan agregat untuk halaman Ringkasan SDM |

Aturan implementasi yang tidak boleh dilanggar:

- Gunakan `scaler.transform`, **bukan** `fit_transform`, dengan `pd.DataFrame` berkolom sama dan berurutan seperti `FEATURES` pada training.
- Nomor klaster, persona, tingkat risiko, dan warna **dibaca dari `cluster_profiles.json`**, tidak ditulis manual, karena label K-Means bisa bergeser setelah training ulang.
- `predict_one` dan `predict_batch` memakai jalur yang sama, sehingga hasilnya identik untuk data yang sama.

### Aturan rekomendasi tambahan

Dievaluasi setelah klaster ditentukan; persona dicocokkan lewat nama persona di JSON.

| Kode | Kondisi | Rekomendasi tambahan |
| --- | --- | --- |
| R1 | Persona High Burnout dan (jam > 250 atau proyek ≥ 6) | Redistribusi proyek, batasi lembur, cuti pemulihan, tinjau kompensasi/promosi |
| R2 | Persona Disengaged dan evaluasi < 0,60 | Sesi 1-on-1 coaching, asesmen role fit, reskilling |
| R3 | Persona Engaged Stars dan evaluasi ≥ 0,80 | Jalur leadership fast-track, insentif retensi, jadi mentor |
| R4 | Persona Senior Veteran dan promosi 5 tahun = tidak | Tinjau jenjang jabatan/tunjangan senioritas, rotasi proyek strategis |
| R5 | Semua klaster, kepuasan < 0,35 | Konseling HR dalam 7 hari kerja sebagai peringatan dini |

Aturan ini adalah kebijakan heuristik tim, bukan keluaran model; sebutkan itu saat presentasi.

## 8. Validasi dan Penanganan Error

| Situasi | Perilaku aplikasi |
| --- | --- |
| Slider di Deteksi Karyawan | Rentang dibatasi widget, jadi tidak ada input tidak valid |
| CSV bukan `.csv` atau > 5 MB | Pesan `st.error`, proses berhenti |
| Kolom fitur hilang di CSV | `st.error` berisi daftar kolom yang kurang |
| Baris kosong atau di luar rentang | Baris dilaporkan di tabel "baris ditolak", baris lain tetap diproses |
| Nilai di luar rentang dataset tapi masih wajar | Diproses, dengan `st.warning` |
| Artefak atau dataset tidak ditemukan | `st.error` menyebut file yang hilang dan perintah `python train_pipeline.py`, lalu `st.stop()` |

## 9. Persyaratan Non-Fungsional

- Halaman pertama tampil < 3 detik setelah model ter-cache.
- Prediksi satu karyawan terasa instan; batch 10.000 baris < 5 detik.
- Tema warna konsisten: navy `#1E3A8A`, teal `#0D9488`, dan merah/amber untuk indikator risiko.
- Seluruh teks antarmuka dalam bahasa Indonesia.
- README memuat cara menjalankan dalam beberapa perintah: `pip install -r requirements.txt`, `python train_pipeline.py`, `streamlit run app.py`.
- Deploy bersifat opsional (Streamlit Community Cloud lewat repositori GitHub; folder `artifacts/` dan `data/` harus ikut di-commit). Untuk demo, jalan lokal sudah cukup.

## 10. Pengujian dan Kriteria Penerimaan

### Test otomatis (pytest, hanya `core/`)

1. `load_artifacts()` berhasil dan jumlah klaster sama dengan `optimal_k` di JSON.
2. `predict_one` untuk profil burnout (kepuasan rendah, jam tinggi, proyek 6) menghasilkan persona High Burnout; nilai uji diambil dari output model sendiri, bukan angka PPT teman.
3. 50 baris acak lewat `predict_one` satu per satu sama dengan hasil `predict_batch`.
4. Batch dengan satu baris rusak tetap memproses baris lain dan melaporkan baris rusak.
5. Kolom `average_monthly_hours` (ejaan benar) tetap diterima.

### Kriteria penerimaan

- [ ] Empat halaman berjalan tanpa error di `streamlit run app.py`.
- [ ] Semua test di atas lulus.
- [ ] Alur demo lancar: buka Ringkasan, lihat Peta Klaster, coba satu karyawan, unggah CSV, unduh hasil.
- [ ] Seluruh angka yang dipresentasikan berasal dari satu kali run `train_pipeline.py` yang sama dengan isi `artifacts/`.
- [ ] README selesai.

## 11. Pembagian Kerja

Karena frontend dan backend kini satu proyek, pembagian paling aman adalah per folder dengan fungsi `core/` sebagai kontrak:

- **Backend (kamu):** seluruh `core/`, `tests/`, `README.md`, dan pengecekan artefak.
- **Frontend (teman):** `app.py`, `pages/`, dan tema `.streamlit/config.toml`.
- Kontrak: nama dan bentuk keluaran fungsi di bagian 7. Teman bisa mulai dengan fungsi tiruan yang mengembalikan data contoh sampai `core/` selesai.

## 12. Timeline

| Hari | Target |
| --- | --- |
| **Selasa 24 Nov** | Jalankan `train_pipeline.py` di data sendiri dan catat K optimal. Buat kerangka proyek, `artifacts.py`, `predictor.py`, dan `validate_input`. Kirim daftar fungsi bagian 7 ke teman. |
| **Rabu 25 Nov** | `recommender.py`, `data.py` (agregat EDA), `predict_batch`, `charts.py`, test pytest. Halaman Deteksi Karyawan dan Audit Massal terhubung ke `core/`. |
| **Kamis 26 Nov (pagi)** | Integrasi semua halaman, perbaikan bug, bekukan kode, latihan demo. Tidak ada fitur baru. |

Jika waktu mepet, urutan prioritas: Deteksi Karyawan, Peta Klaster, Ringkasan SDM, Audit Massal, radar chart.

## 13. Risiko dan Mitigasi

| Risiko | Mitigasi |
| --- | --- |
| Versi scikit-learn beda antara training dan aplikasi | Pin versi di `requirements.txt` |
| Streamlit menjalankan ulang skrip tiap interaksi, aplikasi terasa lambat | Cache model dan agregat; gunakan `st.form` dan `st.session_state` |
| Nomor klaster bergeser setelah training ulang | Persona dibaca dari JSON, tidak ditulis manual |
| Angka PPT tidak cocok dengan hasil data sendiri | Ambil semua angka dari output pipeline sendiri |
| Konflik kode antar anggota di satu repo | Pembagian per folder (bagian 11) dan commit kecil |

## 14. Pertanyaan Terbuka

- Duplikat 3.008 baris dipertahankan (sesuai script saat ini) atau dihapus? Ini memengaruhi angka di Ringkasan SDM dan harus sama dengan laporan.
- Apakah radar chart wajib ada, atau cukup tabel profil klaster?
