# PRD SI-REKARYA — FastAPI dan UI Custom

**Status:** Rancangan produk untuk migrasi dari Streamlit  
**Bahasa antarmuka:** Bahasa Indonesia  
**Target:** Demo lokal dan pengembangan UI lanjutan

## 1. Ringkasan

SI-REKARYA adalah dashboard analitik SDM yang mengelompokkan karyawan berdasarkan
pola karakteristik kerja dan menampilkan indikator risiko keluar. Versi baru
mengganti antarmuka Streamlit dengan **FastAPI, template Jinja2, HTMX, CSS, dan
Chart.js** agar tata letak, interaksi, dan visualisasi dapat dirancang khusus
tanpa membangun single-page application besar.

Model terlatih, artefak, dan logika analitik yang sudah ada tetap menjadi sumber
kebenaran. Migrasi mengubah cara aplikasi menyajikan dan menerima data; bukan
melatih ulang atau mengubah aturan prediksi.

## 2. Masalah dan Tujuan

### Masalah

- Komponen dan tata letak Streamlit membatasi kendali visual untuk dashboard
  yang sangat disesuaikan.
- Grafik model mudah terlihat teknis dan sulit ditafsirkan oleh audiens awam.
- Informasi penting seperti risiko, konteks jumlah karyawan, dan tindak lanjut
  perlu lebih menonjol daripada metrik algoritme.

### Tujuan

1. Memberikan UI responsif dan konsisten yang dapat dikustomisasi dengan HTML
   dan CSS.
2. Menjelaskan setiap hasil dengan bahasa sehari-hari dan konteks data.
3. Menyajikan empat alur: ringkasan, persona/peta, deteksi satu karyawan, dan
   audit CSV massal.
4. Mempertahankan kesesuaian hasil prediksi dengan pipeline dan artefak saat ini.
5. Menggunakan stack frontend ringan tanpa React/Vue dan tanpa proses build
   JavaScript wajib.

### Bukan tujuan

- Mengubah atau melatih ulang K-Means, scaler, atau PCA dari aplikasi.
- Menambah login, database, penyimpanan historis, atau deployment publik pada
  tahap demo ini.
- Menggunakan skor model untuk membuat keputusan otomatis terhadap karyawan.
- Mengganti rekomendasi HR berbasis aturan dengan keluaran AI generatif.

## 3. Pengguna dan Prinsip UX

### Pengguna utama

- **Presenter/HR:** ingin mengetahui pola, risiko, dan tindakan yang dapat
  dipertimbangkan tanpa perlu memahami algoritme.
- **Dosen/evaluator:** ingin melihat bahwa hasil berasal dari model dan data
  yang konsisten, serta detail teknis tersedia saat diperlukan.

### Prinsip

- **Kesimpulan dulu:** judul grafik menyampaikan temuan, bukan nama tipe grafik.
- **Angka selalu berkonteks:** persentase penting disertai jumlah sampel bila
  ukuran kelompok memengaruhi interpretasi.
- **Teknis bertahap:** istilah K, PCA, centroid, jarak, Silhouette, DBI, dan
  WCSS hanya muncul di area detail teknis.
- **Warna bukan satu-satunya petunjuk:** label risiko dan persona selalu
  ditampilkan bersama warna dan teks.
- **Tidak menghakimi individu:** hasil adalah indikator historis kelompok,
  bukan kepastian bahwa seorang karyawan akan keluar.

## 4. Ruang Lingkup Produk

### Termasuk

- Empat halaman dashboard dengan navigasi yang jelas.
- Form prediksi individual dan rekomendasi HR berbasis aturan yang sudah ada.
- Unggah CSV, validasi, distribusi persona, pratinjau hasil, dan unduhan CSV.
- Visualisasi yang menggunakan format angka Indonesia.
- Panel detail teknis yang dapat dibuka pengguna.

### Tidak termasuk

- Autentikasi dan otorisasi multipengguna.
- Database, penyimpanan permanen hasil, atau riwayat audit.
- Konektor HRIS, email, notifikasi, atau integrasi pihak ketiga.
- Fitur untuk mengubah profil, risiko, atau aturan rekomendasi dari UI.

## 5. Arsitektur dan Teknologi

### Stack yang dipilih

| Lapisan | Teknologi | Tanggung jawab |
|---|---|---|
| Web server | FastAPI | Routing, validasi request, pemanggilan pipeline |
| Template | Jinja2 | HTML server-rendered dan komponen bersama |
| Interaksi | HTMX | Submit form dan pembaruan bagian halaman tanpa SPA |
| Gaya | CSS biasa | Token desain, layout responsif, komponen UI |
| Visualisasi | Chart.js | Grafik dashboard yang mudah dipahami |
| Analitik | Modul `core/` yang ada | Model, transformasi, data, dan rekomendasi |

Tidak diperlukan React/Vue, bundler JavaScript, atau database untuk rilis demo.
JavaScript khusus ditambahkan hanya bila interaksi Chart.js atau HTMX tidak
mencukupi.

### Batas arsitektur

- Pertahankan `core/` sebagai sumber kebenaran untuk model, prediksi,
  rekomendasi, pemuatan data, dan artefak.
- Lapisan web mengubah hasil `core/` menjadi view model yang aman untuk template
  dan grafik; template tidak menjalankan logika model.
- Jangan mengubah signature fungsi atau format artefak model kecuali ada
  kebutuhan yang dibuktikan dan disetujui terpisah.
- Gunakan helper format angka bersama untuk tabel, kartu KPI, dan data grafik.
- Halaman awal tetap dapat dirender di server; HTMX meningkatkan interaksi,
  bukan menjadi ketergantungan untuk membaca konten utama.

### Struktur aplikasi yang disarankan

```text
app/
  main.py
  routes/
  services/
  templates/
    base.html
    components/
  static/
    css/
    js/
```

Struktur ini merupakan usulan. Implementasi harus menyesuaikan pola proyek yang
ada dan tidak memindahkan `core/` tanpa alasan teknis.

## 6. Navigasi dan Halaman

Navigasi utama memuat **Ringkasan SDM**, **Persona & Peta**, **Deteksi
Karyawan**, dan **Audit Data Massal**. Branding hanya berada di sidebar.
Setiap halaman memiliki satu judul dan satu kalimat penjelasan, dengan lebar
konten maksimum sekitar 1.200 px.

### 6.1 Ringkasan SDM

**Tujuan:** memberi gambaran cepat tentang jumlah karyawan dan pola turnover.

- Tampilkan KPI utama dengan label singkat, angka besar, dan format Indonesia.
- Tempatkan kotak **Temuan utama** berisi 2–3 poin yang dihitung dari data di
  atas grafik.
- Grafik proyek menampilkan persentase karyawan keluar menurut jumlah proyek
  menggunakan satu bar horizontal. Warnai merah untuk tingkat di atas 30% dan
  teal untuk nilai lainnya; sertakan jumlah karyawan (`n`) per kelompok.
- Hubungan jam kerja dan kepuasan ditampilkan sebagai heatmap/bin atau scatter
  maksimal 1.500 titik dengan opacity rendah. Beri anotasi pada pola yang
  benar-benar didukung data.
- Judul grafik berupa kesimpulan yang terukur, bukan nama jenis grafik. Hindari
  judul berulang di luar dan di dalam grafik.

### 6.2 Persona & Peta

**Tujuan:** menjelaskan empat kelompok karyawan sebelum menampilkan posisi
relatifnya.

- Tab pertama menampilkan empat kartu persona. Setiap kartu berisi nama persona,
  warna/badge, persentase karyawan, persentase historis yang keluar, tingkat
  risiko, dan karakteristik dalam bahasa awam.
- Tab kedua menampilkan **peta kemiripan karyawan**, dengan rasio mendekati
  16:9, tinggi minimum 520 px, maksimal 2.000 titik, dan opacity sekitar 0,5.
- Gunakan warna persona yang mudah dibedakan (teal, merah, amber gelap, navy)
  serta bentuk marker berbeda agar tetap terbaca di proyektor.
- Label pusat kelompok menggunakan nama persona dengan kotak latar putih; jangan
  menampilkan istilah “Centroid N” pada tampilan utama.
- Nilai K dan varians PCA hanya ada di tab/expander **Detail teknis**, disertai
  satu kalimat arti masing-masing metrik.

### 6.3 Deteksi Karyawan

**Tujuan:** memberi interpretasi kelompok dan rekomendasi untuk satu profil,
tanpa menyatakan hasil sebagai kepastian individual.

- Satu kartu hasil utama menampilkan nama persona, badge risiko, serta kalimat
  “Dari 100 karyawan serupa, sekitar X pernah keluar” berdasarkan turnover
  historis kelompok.
- Urutan hasil: kartu persona → rekomendasi HR → perbandingan input dengan
  rata-rata kelompok → peta posisi.
- Rekomendasi HR berbasis aturan yang sudah ada disajikan sebagai checklist
  berprioritas dengan teks yang mudah dibaca.
- Perbandingan input dan rata-rata kelompok memakai bar berdampingan dengan
  label yang jelas dan skala yang dapat dipahami.
- Peta posisi dapat ditempatkan di bawah hasil atau dalam expander. Marker
  karyawan yang dideteksi lebih besar dan memiliki outline putih.
- Jarak ke pusat kelompok dan skor kepuasan mentah hanya ditampilkan dalam
  **Detail teknis**.

### 6.4 Audit Data Massal

**Tujuan:** memproses CSV secara transparan dan membantu pengguna memeriksa hasil.

- Stepper memiliki tiga langkah dan menyorot status aktif:
  1. Siapkan file: contoh 2–3 baris format CSV dan tombol unduh template.
  2. Unggah file: validasi, ringkasan kesalahan, dan status proses.
  3. Tinjau hasil: KPI diproses/ditolak, distribusi persona, tabel, dan unduhan.
- Distribusi persona menggunakan donut atau bar chart dengan label dan jumlah.
- Kolom `Risk_Level` pada tabel diberi warna dan teks, bukan warna saja.
- Tombol unduh hasil dibuat menonjol dan diberi nama file yang informatif.
- Baris yang ditolak disertai alasan validasi yang dapat ditindaklanjuti; jangan
  menghilangkan kegagalan secara diam-diam.

## 7. Format Data dan Kontrak Web

### Halaman

| Metode dan path | Fungsi |
|---|---|
| `GET /` | Ringkasan SDM |
| `GET /personas` | Kartu persona dan peta kemiripan |
| `GET /detect` | Form deteksi satu karyawan |
| `POST /detect` | Validasi input dan tampilkan hasil prediksi |
| `GET /audit` | Form dan petunjuk audit CSV |
| `POST /audit` | Validasi dan proses CSV |
| `GET /audit/download/{token}` | Unduh hasil audit sementara |
| `GET /health` | Health check sederhana untuk proses web |

Form server-rendered harus tetap dapat digunakan tanpa JavaScript. Respons
HTMX boleh mengembalikan partial HTML untuk pembaruan hasil, tetapi bentuk data
internal harus memiliki tipe dan batas yang jelas. Jangan mengekspos detail
exception atau path lokal melalui respons.

### Validasi CSV

- Batas ukuran file: **5 MB**.
- Batas jumlah baris data: **20.000**.
- Pertahankan alias kolom `average_monthly_hours` yang sudah diterima pipeline.
- Validasi keberadaan kolom, tipe/nilai, dan baris kosong sebelum prediksi.
- Tampilkan jumlah baris diterima/ditolak dan alasan penolakan per baris.
- Jangan memproses file di atas batas; sampaikan batas dengan jelas.

### Unduhan sementara

- Hasil audit tidak disimpan permanen atau ke database.
- Gunakan token acak yang sulit ditebak dan cache memori dengan TTL 15 menit
  untuk menghubungkan hasil dengan unduhan.
- Setelah TTL, token kedaluwarsa dan unduhan memberikan respons yang sesuai.
- Tetapkan nama file dan content type CSV secara eksplisit.

## 8. Bahasa, Angka, dan Aksesibilitas

- Gunakan Bahasa Indonesia yang konsisten; ganti istilah teknis pada tampilan
  utama dengan istilah awam. Contoh: “pusat kelompok” dan “peta kemiripan
  karyawan”.
- Gunakan format lokal: pemisah ribuan titik, desimal koma, dan satuan yang
  sesuai (contoh `14.999`, `23,8%`, `0,61`, `201 jam`).
- Sasaran tipografi: isi 16 px, caption 14 px, label KPI 13 px, angka KPI
  minimal 36 px, judul grafik 18 px, label slider 15 px, serta legend dan tick
  sumbu 13 px.
- Kontras teks normal minimal 4,5:1. Tombol primer memakai teks putih tebal
  pada navy/teal dengan kontras yang lolos pemeriksaan.
- Grafik memiliki judul bermakna, legenda, label/tooltip yang informatif, dan
  ringkasan teks yang dapat dibaca tanpa mengandalkan warna.
- Tata letak harus responsif untuk laptop dan proyektor; hindari grafik gepeng,
  label kecil, dan scroll horizontal yang tidak perlu.

## 9. Privasi dan Batas Keselamatan Produk

- Aplikasi tahap demo berjalan lokal dan tidak membutuhkan autentikasi publik.
- Data karyawan hanya digunakan untuk permintaan saat itu; jangan mencatat
  nilai profil atau isi CSV ke log.
- Hasil audit hanya tersedia sementara melalui token ber-TTL, sesuai batas
  penyimpanan pada PRD ini.
- Pesan error untuk pengguna tidak boleh memuat traceback, secret, atau path
  file internal.
- Tegaskan bahwa indikator turnover adalah pola historis kelompok dan bukan
  keputusan atau kepastian terhadap individu.
- Sediakan instruksi untuk tidak mengunggah data yang tidak berwenang digunakan.

## 10. Kinerja dan Reliabilitas

- Halaman ringkasan dan persona tidak menghitung ulang model pada setiap render
  jika data/artefak tidak berubah.
- Terapkan batas unggahan sebelum membaca seluruh file ke memori.
- Proses audit 20.000 baris harus selesai dengan status yang jelas dan tidak
  membuat halaman tampak macet tanpa umpan balik.
- Kegagalan pemuatan artefak atau validasi dilaporkan eksplisit; jangan
  menghasilkan respons sukses kosong.
- Health check hanya menyatakan status web/dependensi yang relevan dan tidak
  mengungkap informasi sensitif.

## 11. Kriteria Penerimaan

1. Empat halaman dapat dibuka dan dinavigasi melalui FastAPI tanpa error.
2. Halaman utama memiliki satu judul dan satu deskripsi; branding tidak
   berulang di area konten.
3. Semua angka utama dan data grafik menggunakan format angka Indonesia.
4. Ringkasan menampilkan 2–3 temuan berbasis data dan grafik proyek berupa bar
   horizontal dengan persentase serta `n`.
5. Tab pertama Persona & Peta memuat empat kartu persona; tab peta mengikuti
   batas rasio, tinggi, jumlah titik, label, warna, dan marker yang ditetapkan.
6. Deteksi menunjukkan kartu persona, probabilitas historis kelompok dalam
   bahasa awam, rekomendasi, perbandingan input/rata-rata, dan peta posisi.
7. Metrik teknis hanya tersedia pada bagian **Detail teknis**.
8. Audit CSV menolak file di atas batas, melaporkan baris yang ditolak, dan
   menyediakan tabel serta unduhan hasil untuk data yang valid.
9. Token unduhan kedaluwarsa setelah 15 menit dan hasil tidak tersimpan
   permanen.
10. Kontras tombol primer memenuhi minimal 4,5:1 dan kontrol utama berfungsi
    dengan keyboard.
11. Prediksi individual dan massal konsisten dengan pemanggilan pipeline/artefak
    yang digunakan versi saat ini.
12. Pengujian mencakup validasi input, batas CSV, token unduhan, perenderan
    halaman, serta kasus kegagalan artefak.

## 12. Tahapan Migrasi

1. **Fondasi web:** tambah FastAPI, template dasar, navigasi, static assets,
   health check, dan uji aplikasi.
2. **Ringkasan:** buat view model agregat, helper format angka, dan grafik
   ringkasan.
3. **Persona:** tampilkan kartu persona dan peta kemiripan dengan data pipeline
   yang sama.
4. **Deteksi:** migrasikan validasi form, rekomendasi, perbandingan, dan peta
   posisi; verifikasi hasil terhadap versi lama.
5. **Audit CSV:** migrasikan upload, validasi, hasil, dan unduhan bertoken
   sementara.
6. **Cutover:** jalankan pengujian regresi, pemeriksaan aksesibilitas dan
   kontras, lalu dokumentasikan cara menjalankan aplikasi baru.

Migrasi dilakukan bertahap. Streamlit tidak dihapus sampai seluruh kriteria
penerimaan lulus dan pemilik proyek menyetujui cutover.

## 13. Keputusan dan Hal yang Perlu Disetujui

- PRD ini menetapkan FastAPI, Jinja2, HTMX, CSS biasa, dan Chart.js sebagai
  stack target; dependensi baru baru ditambahkan saat implementasi dimulai.
- PRD Streamlit sebelumnya bukan lagi sumber requirement untuk migrasi;
  perubahan historisnya dapat ditinjau melalui riwayat Git.
- TTL unduhan ditetapkan 15 menit dan batas CSV ditetapkan 5 MB/20.000 baris;
  perubahan batas memerlukan persetujuan produk.
- Istilah persona, ambang badge risiko, serta nama variabel yang ditampilkan
  perlu dicocokkan dengan data dan artefak aktual sebelum implementasi UI.
- Detail deployment di luar demo lokal, autentikasi, dan persistensi belum
  termasuk dalam keputusan produk ini.
