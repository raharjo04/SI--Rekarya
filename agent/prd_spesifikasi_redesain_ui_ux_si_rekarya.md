# PRD Spesifikasi Redesain UI/UX SI-REKARYA

**Tanggal:** 24 November 2026  
**Target Aplikasi:** Streamlit (Python 3.11)  
**Status:** Panduan Redesain Antarmuka Modern & Professional Dashboard  

---

## 1. Latar Belakang & Masalah UI Saat Ini

Tampilan default Streamlit bawaan terasa sangat polos, kurang penegakan hierarki visual, dan terkesan seperti skrip uji coba internal. Untuk keperluan presentasi eksekutif dan penilaian dosen, aplikasi memerlukan perombakan UI/UX agar terlihat seperti **Enterprise HR Analytics Dashboard**.

---

## 2. Sistem Desain & Identitas Visual

### 2.1 Palet Warna Sintetis (Semantic Color Palette)
Semua elemen visual (kartu, badge, grafik Plotly, dan indikator risiko) wajib mematuhi skema warna berikut:

| Peran Warna | Hex Code | Penggunaan UI |
| :--- | :--- | :--- |
| **Primary Navy** | `#1E3A8A` | Header utama, tombol primary, Klaster *Engaged Stars*, aksen navigasi |
| **Secondary Teal** | `#0D9488` | Sub-header, grafik sekunder, Klaster *Senior Veteran*, elemen sukses |
| **Alert Red (High Risk)** | `#DC2626` | Badge *High Burnout*, indikator bahaya, peringatan R1 & R5 |
| **Warning Amber (Medium Risk)**| `#D97706` | Badge *Disengaged*, indikator perhatian |
| **Background Dark/Light** | `#F8FAFC` / `#0F172A` | Background aplikasi (dukung mode bersih Slate Light) |
| **Card Surface** | `#FFFFFF` | Background kontainer/card dengan kontras tinggi |
| **Text Primary & Secondary** | `#1E293B` / `#64748B` | Judul teks utama dan subtitle/keterangan |

---

## 3. Blueprint Injeksi Custom CSS (`core/ui_theme.py`)

Gunakan pembungkus CSS global yang dipanggil di `app.py` dan setiap file di `pages/` via `st.markdown(..., unsafe_allow_html=True)`.

```python
import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
    /* 1. Pengaturan Layout Main Container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    /* 2. Custom Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetricLabel"] > div {
        color: #64748B !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] > div {
        color: #1E3A8A !important;
        font-size: 1.875rem !important;
        font-weight: 700 !important;
    }

    /* 3. Custom Container Card */
    .css-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* 4. Custom Badges untuk Risk Level */
    .badge-risk-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        border: 1px solid #FCA5A5;
    }
    .badge-risk-medium {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        border: 1px solid #FCD34D;
    }
    .badge-risk-low {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        border: 1px solid #93C5FD;
    }

    /* 5. Styling Form & Tombol Submit */
    div[data-testid="stForm"] {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        background-color: #FFFFFF;
    }
    .stButton > button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 10px 24px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #1D4ED8;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);
    }
    </style>
    """, unsafe_allow_html=True)
```

---

## 4. Standar Tema Grafik Plotly (`core/charts.py`)

Setiap fungsi di `core/charts.py` wajib menerapkan templat Plotly yang seragam:

1. **Background Transparent / Clean White**:
   - `paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`.
2. **Grid Lines**:
   - Warna grid halus `#F1F5F9` pada sumbu X dan Y.
3. **Font**:
   - Font family: `Inter, -apple-system, sans-serif`.
4. **Hover Template Custom**:
   - Tampilkan label informasi yang jelas tanpa string format bawaan Plotly yang berantakan.

---

## 5. Layout & Redesain Detail Per Halaman

### 5.1 Halaman 1: Ringkasan SDM (`1_Ringkasan_SDM.py`)
- **Header Section:** Title besar "Ringkasan Eksekutif SDM" dengan subtitle menjelaskan cakupan dataset.
- **KPI Metrics (Top Row):**
  - Gunakan `st.columns(4)`.
  - Tampilkan 4 `st.metric`: Total Karyawan, Turnover Rate (%), Rata-rata Kepuasan, Rata-rata Jam Kerja.
- **Visual Section 1 (2-Column Grid):**
  - Kolom Kiri (`col1`): Scatter Plot Jam Kerja vs Kepuasan (Warna berdasarkan `Left`/Turnover). Dibungkus `st.container(border=True)`.
  - Kolom Kanan (`col2`): Bar Chart Distribusi Jumlah Proyek vs Turnover Rate. Dibungkus `st.container(border=True)`.
- **Insight Callout Box:** `st.info()` di bagian bawah yang merangkum poin utama dari data.

---

### 5.2 Halaman 2: Peta Klaster (`2_Peta_Klaster.py`)
Gunakan struktur **Tabs** agar halaman tidak terlalu panjang digulir:
- **Tab 1: Visualisasi Klaster PCA 2D**
  - Kartu ringkasan K terpilih (K=4) & Varians PCA yang dijelaskan ($PC_1 + PC_2$).
  - Scatter plot PCA 2D ukuran besar dengan titik centroid yang kontras (simbol bintang/berlian besar).
- **Tab 2: Evaluasi Model (K=2..8)**
  - Grafik Elbow & Silhouette diletakkan berdampingan (`st.columns(2)`).
  - Tabel evaluasi lengkap di mana baris $K=4$ disorot dengan warna khusus.
- **Tab 3: Profil & Strategi Klaster**
  - Grid 2x2 kartu profil klaster (`High Burnout`, `Disengaged`, `Senior Veteran`, `Engaged Stars`).
  - Di dalam setiap kartu:
    - Persona Badge + Turnover Rate.
    - Metrik rata-rata fitur asli.
    - Expander bertuliskan `"Rekomendasi Strategi HR"` berisi poin-poin konkret.

---

### 5.3 Halaman 3: Deteksi Karyawan (`3_Deteksi_Karyawan.py`)
Gunakan **Split-Screen Layout (Layout 2 Kolom)**:

- **Kolom Kiri (Input Form - 40% Lebar):**
  - Judul: `"Input Parameter Karyawan"`.
  - Form pembungkus `st.form(key="prediction_form")`.
  - Grouping Slider dengan penataan yang rapi:
    - *Seksi Kepuasan & Evaluasi*: Slider `satisfaction_level` & `last_evaluation`.
    - *Seksi Beban Kerja*: Slider `number_project` & `average_montly_hours`.
    - *Seksi Masa Kerja & Karir*: Slider `time_spend_company` & Checkbox `promoted_last_5years`.
  - Tombol Submit `"Jalankan Analisis Karyawan"` (memenuhi lebar kolom/full width).

- **Kolom Kanan (Hasil Prediksi & Rekomendasi - 60% Lebar):**
  - Jika belum di-submit: Tampilkan *empty state placeholder* dengan ilustrasi/info panduan.
  - Jika sudah di-submit:
    - **Header Hasil:** Badge Persona Besar + Status Tingkat Risiko (Merah/Amber/Navy).
    - **Metric Highlight Cards (3 kolom kecil):** Jarak Centroid, Turnover Historis Klaster, Skor Kepuasan.
    - **Visualisasi PCA Position:** Scatter PCA 2D yang menyoroti posisi karyawan baru ini (titik menyala/animasi glow) di tengah klaster lainnya.
    - **Kartu Rekomendasi HR:** Box khusus berisi daftar aturan R1-R5 yang terpicu dalam format *bullet list* dengan icon checklist.

---

### 5.4 Halaman 4: Audit Data Massal (`4_Audit_Data_Massal.py`)
- **Header Section:** Tombol Unduh Template CSV diletakkan sejajar di kanan atas header.
- **Upload Dropzone Section:**
  - `st.file_uploader` dibungkus container bersih dengan keterangan batas file (Maks 5 MB & 20.000 baris).
- **Audit Execution & Summary Dashboard:**
  - Tampilkan 3 kartu status pasca-upload:
    1. Total Baris Diproses (Hijau).
    2. Baris Valid (Teal).
    3. Baris Ditolak/Invalid (Merah).
  - Jika ada baris ditolak: Tampilkan `st.dataframe` khusus di dalam `st.expander("Lihat Detail Baris yang Ditolak")`.
- **Hasil Massal Section:**
  - **Grafik Distribusi Klaster Hasil Batch:** Pie chart / Donut chart persentase klaster hasil prediksi massal.
  - **Pratinjau Data Result Table:** `st.dataframe` dengan fitur filter kolom.
  - **Action Button:** Tombol `st.download_button` besar berwarna hijau/navy untuk mengunduh CSV hasil audit.

---

## 6. Prompt Siap Pakai Untuk Meminta AI Memperbaiki UI (`pages/`)

Berikan prompt ini kepada AI coding assistant untuk mengimplementasikan spesifikasi di atas:

> **Prompt Instuksi Refactoring UI:**
> *"Tolong perbaiki kode UI Streamlit pada folder `pages/` berdasarkan `@PRD_UI_UX_SI_REKARYA.md`.
> **Syarat Utama:**
> 1. Impor dan jalankan `inject_custom_css()` dari `core/ui_theme.py` di awal setiap file halaman.
> 2. Ganti semua layout polos dengan `st.container(border=True)` atau kolom berdampingan (`st.columns`) sesuai spesifikasi layout di PRD UI/UX.
> 3. Gunakan `st.metric` dengan format angka yang rapi.
> 4. Pada Halaman Deteksi Karyawan, buat tampilan split-screen (kolom kiri form input, kolom kanan hasil visualisasi dan rekomendasi HR).
> 5. Pastikan semua grafik Plotly menggunakan template transparan/bersih dengan palet warna Navy (`#1E3A8A`) dan Teal (`#0D9488`)."*