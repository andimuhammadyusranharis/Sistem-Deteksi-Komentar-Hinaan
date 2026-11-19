# Sistem Deteksi Komentar Hinaan Menggunakan Jaringan Syaraf Tiruan

Proyek Akhir Mata Kuliah **Kecerdasan Buatan (2026)**.  
Aplikasi web sederhana berbasis **Python Flask** dan **Jaringan Syaraf Tiruan (Multi-Layer Perceptron)** untuk mendeteksi apakah sebuah komentar berbahasa Indonesia termasuk ke dalam kelas **Menghina** atau **Bukan Menghina**.

---

## 1. Fitur Utama Aplikasi

1. **Input & Validasi Komentar:** Menerima masukan teks komentar berbahasa Indonesia (minimal 3 kata, maksimal 500 karakter, dan wajib mengandung huruf).
2. **Deteksi dengan Jaringan Syaraf Tiruan (JST):** Menghitung skor probabilitas komentar menghina (`0,00` – `1,00`) menggunakan ekstraksi fitur **TF-IDF (3.000 fitur)** dan **MLPClassifier (1 hidden layer, 16 neuron, aktivasi sigmoid)** dengan ambang batas keputusan `0,50`.
3. **Penjelasan Hasil (*Explainability*):**
   - **Kata terdeteksi:** Mencocokkan kata pada komentar dengan daftar kata kasar (`abusive.csv`).
   - **Pengaruh terbesar:** Menampilkan kata yang paling memengaruhi kenaikan skor JST pada komentar tersebut (menggunakan metode *word occlusion*, yaitu menghitung selisih penurunan skor saat kata tersebut dihapus).
4. **Ringkasan Evaluasi Model:** Menampilkan jumlah data bersih, akurasi pada data uji, perbandingan dengan *baseline*, matriks evaluasi (*confusion matrix*), dan arsitektur model.

---

## 2. Struktur Folder Proyek

```text
PROJEK_UAS/
├── app.py                      # Aplikasi utama web Flask (validasi, prediksi, penjelasan hasil)
├── train_jst.py                # Skrip praproses data, pelatihan JST, evaluasi, dan penyimpanan model
├── model_jst.joblib            # Berkas model JST, TF-IDF, kamus, dan metrik hasil pelatihan
├── re_dataset.csv              # Dataset publik Ibrohim & Budi (2019) - 13.169 tweet
├── new_kamusalay.csv           # Kamus pembakuan kata gaul/alay bahasa Indonesia
├── abusive.csv                 # Daftar kata kasar bahasa Indonesia
├── requirements.txt            # Daftar pustaka Python yang dibutuhkan
├── .gitignore                  # Pengaturan berkas yang diabaikan oleh Git
├── templates/
│   └── index.html              # Halaman antarmuka pengguna (HTML + Jinja2)
├── static/
│   └── css/
│       └── style.css           # Desain tampilan antarmuka (CSS) 
└── x_comment_scraper/
    ├── buat_berkas_label.py    # Skrip pembuat berkas Excel pelabelan tanpa identitas penulis
    ├── pelabelan_komentar.xlsx # Lembar kerja pelabelan 100 komentar uji tambahan (tanpa username)
    └── scrape_x_comments.py    # Skrip pengambil data uji tambahan
```

---

## 3. Petunjuk Menjalankan Aplikasi

### A. Prasyarat
Pastikan komputer sudah terpasang **Python 3.10 atau lebih baru**.

### B. Langkah Instalasi
1. **Clone repositori ini** (atau unduh dan ekstrak folder proyek):
   ```bash
   git clone https://github.com/andimuhammadyusranharis/Sistem-Deteksi-Komentar-Hinaan.git
   cd PROJEK_UAS
   ```

2. **(Opsional tapi disarankan) Buat dan aktifkan Virtual Environment:**
   - **Windows (PowerShell / CMD):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Pasang seluruh pustaka yang dibutuhkan (`requirements.txt`):**
   ```bash
   pip install -r requirements.txt
   ```

### C. Melatih Ulang Model JST (Opsional)
Berkas `model_jst.joblib` sudah disertakan sehingga aplikasi dapat langsung dijalankan. Namun jika ingin menjalankan ulang proses pelatihan dari awal:
```bash
python train_jst.py
```
Skrip ini akan membaca `re_dataset.csv`, membersihkan teks, membagi data (80% latih, 20% uji), melatih JST, menampilkan hasil evaluasi di terminal, dan memperbarui `model_jst.joblib`.

### D. Menjalankan Aplikasi Web Flask
Jalankan perintah berikut di terminal:
```bash
python app.py
```
Kemudian buka browser dan akses alamat:
```text
http://127.0.0.1:8000
```

---

## 4. Ringkasan Metode dan Kinerja Model

- **Sumber Data Latih & Uji:** Dataset Ibrohim & Budi (2019), lisensi CC BY-NC-SA 4.0.
- **Aturan Label:** `Menghina (1)` jika `Abusive = 1` atau `HS = 1`; `Bukan Menghina (0)` jika keduanya `0`.
- **Jumlah Data:** 13.169 data awal $\rightarrow$ 332 duplikat dihapus $\rightarrow$ **12.837 data bersih** (10.269 data latih, 2.568 data uji).
- **Kinerja pada Data Uji (2.568 komentar):**
  - **Akurasi Baseline:** 55,5%
  - **Akurasi JST:** 86,1%
  - **F1-Score:** 0,88 (Menghina) dan 0,84 (Bukan Menghina)

---

## 5. Pembagian Tugas Anggota Kelompok

Proyek ini dikerjakan oleh 3 anggota kelompok dengan pembagian tanggung jawab sebagai berikut:

| Anggota | Peran & Tanggung Jawab | Berkas Utama yang Dikerjakan |
| :--- | :--- | :--- |
| **Andi Muh Yusran Haris/250210501003**<br>*(Data & Model AI)* | 1. Menyiapkan dataset publik dan kamus kata gaul/kasar.<br>2. Menyusun fungsi praproses teks (`bersihkan_teks`) dan ekstraksi fitur TF-IDF.<br>3. Melatih model `MLPClassifier` dan menyimpan artefak model. | `train_jst.py`, `re_dataset.csv`, `new_kamusalay.csv`, `abusive.csv`, `model_jst.joblib` |
| **Muh Fathir Alma Arijs/250210501052**<br>*(Aplikasi Web & UI)* | 1. Membangun backend Flask, rute halaman, dan validasi masukan (`validasi_masukan`).<br>2. Mengimplementasikan fungsi prediksi dan penjelasan pengaruh kata (`analisis_komentar`).<br>3. Merancang antarmuka HTML dan CSS sesuai mockup. | `app.py`, `templates/index.html`, `static/css/style.css` |
| **Ade Irmawati/250210500017**<br>*(Pengujian & Dokumentasi)* | 1. Mengoordinasikan pelabelan 100 komentar uji tambahan oleh dua pelabel.<br>2. Melakukan pengujian skenario masukan tidak valid dan analisis kesalahan prediksi model.<br>3. Menyusun proposal, laporan akhir, README, dan bahan presentasi. | `x_comment_scraper/pelabelan_komentar.xlsx`, `docs/Mini Proposal.md`, `README.md` |

> **Catatan Akademik:** Setiap anggota kelompok memahami keseluruhan alur kode (`train_jst.py` dan `app.py`) untuk keperluan presentasi dan tanya jawab individual.

---

## 6. Kredit & Atribusi Dataset (Credits)

Proyek ini menggunakan dataset publik berbahasa Indonesia beserta kamus kata gaul dan daftar kata kasar yang disusun oleh **Muhammad Okky Ibrohim** dan **Indra Budi** (Fakultas Ilmu Komputer, Universitas Indonesia). Kami mengucapkan terima kasih kepada para peneliti atas penyediaan dataset terbuka ini untuk keperluan akademik.

- **Pemilik / Penulis Dataset:** Muhammad Okky Ibrohim & Indra Budi (2019)
- **Berkas yang Digunakan:**
  - `re_dataset.csv` (13.169 tweet berbahasa Indonesia berlabel *Hate Speech* dan *Abusive Language*)
  - `new_kamusalay.csv` (Kamus pembakuan kata tidak baku/gaul bahasa Indonesia)
  - `abusive.csv` (Daftar kata kasar bahasa Indonesia)
- **Repositori Resmi:** [github.com/okkyibrohim/id-multi-label-hate-speech-and-abusive-language-detection](https://github.com/okkyibrohim/id-multi-label-hate-speech-and-abusive-language-detection)
- **Lisensi Dataset:** [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/) — *Digunakan dalam proyek ini murni untuk tujuan pendidikan/non-komersial dengan menyertakan atribusi pemilik asli.*

**Sitasi Makalah (BibTeX / APA):**
> Ibrohim, M. O., & Budi, I. (2019). Multi-label Hate Speech and Abusive Language Detection in Indonesian Twitter. In *Proceedings of the Third Workshop on Abusive Language Online* (pp. 46–57). Association for Computational Linguistics (ACL). https://aclanthology.org/W19-3506/

```bibtex
@inproceedings{ibrohim-budi-2019-multi,
    title = "Multi-label Hate Speech and Abusive Language Detection in {I}ndonesian {T}witter",
    author = "Ibrohim, Muhammad Okky and Budi, Indra",
    booktitle = "Proceedings of the Third Workshop on Abusive Language Online",
    month = aug,
    year = "2019",
    address = "Florence, Italy",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/W19-3506",
    pages = "46--57"
}
```
