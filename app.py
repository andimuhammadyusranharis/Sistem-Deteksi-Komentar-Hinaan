import re
import joblib
from flask import Flask, render_template, request
from train_jst import bersihkan_teks

app = Flask(__name__)

# Muat paket model JST yang sudah dilatih oleh train_jst.py
paket = joblib.load("model_jst.joblib")
jst = paket["jst"]
tfidf = paket["tfidf"]
kamus_alay = paket["kamus_alay"]
daftar_kasar = paket["daftar_kasar"]
info_evaluasi = paket["info_evaluasi"]


# Fungsi untuk memeriksa apakah masukan pengguna valid
def validasi_masukan(teks):
    teks_rapi = teks.strip()
    if not teks_rapi:
        return "Masukan tidak boleh kosong. Silakan tulis komentar terlebih dahulu."

    if len(teks_rapi) > 500:
        return "Komentar terlalu panjang (maksimal 500 karakter)."

    # Cek apakah ada huruf sama sekali (menolak jika hanya angka, simbol, atau emoji)
    if not re.search(r"[a-zA-Z]", teks_rapi):
        return "Komentar harus mengandung huruf, tidak boleh hanya simbol, angka, atau emoji."

    # Hitung jumlah kata yang mengandung huruf (minimal 3 kata)
    kata_huruf = re.findall(r"[a-zA-Z]+", teks_rapi)
    if len(kata_huruf) < 3:
        return "Komentar terlalu pendek. Masukkan minimal 3 kata untuk dianalisis."

    return None


# Fungsi untuk menganalisis komentar menggunakan JST
def analisis_komentar(teks_asli):
    # 1. Praproses teks dan hitung skor (probabilitas) dari JST
    teks_bersih = bersihkan_teks(teks_asli, kamus_alay)
    vektor = tfidf.transform([teks_bersih])
    skor_menghina = float(jst.predict_proba(vektor)[0][1])

    # 2. Tentukan segmen dengan ambang batas (threshold) 0,50
    apakah_menghina = skor_menghina >= 0.50

    # 3. Cari kata kasar yang cocok dengan daftar abusive.csv
    kata_asli = re.findall(r"[a-z0-9]+", teks_asli.lower())
    kata_bersih = teks_bersih.split()
    semua_kata = kata_asli + kata_bersih

    kata_kasar_ditemukan = []
    for k in semua_kata:
        if k in daftar_kasar and k not in kata_kasar_ditemukan:
            kata_kasar_ditemukan.append(k)

    # 4. Hitung kata dengan pengaruh terbesar menuju kelas Menghina (metode occlusion sederhana)
    # Caranya: hapus satu per satu kata dari teks_bersih, lalu lihat kata mana yang paling menurunkan skor menghina
    kata_unik = list(dict.fromkeys(kata_bersih))
    kata_pengaruh = None
    selisih_terbesar = 0.0

    for k in kata_unik:
        sisa_kata = [w for w in kata_bersih if w != k]
        teks_tanpa_k = " ".join(sisa_kata)
        skor_baru = float(jst.predict_proba(tfidf.transform([teks_tanpa_k]))[0][1])
        selisih = skor_menghina - skor_baru

        if selisih > selisih_terbesar:
            selisih_terbesar = selisih
            kata_pengaruh = k

    return {
        "menghina": apakah_menghina,
        "segmen": "Menghina" if apakah_menghina else "Bukan Menghina",
        "skor": skor_menghina,
        "skor_teks": f"{skor_menghina:.2f}".replace(".", ","),
        "persen_bar": round(skor_menghina * 100, 1),
        "kata_kasar": kata_kasar_ditemukan,
        "kata_pengaruh": kata_pengaruh,
        "nilai_pengaruh": f"{selisih_terbesar:+.2f}".replace(".", ","),
        "pengaruh_positif": selisih_terbesar >= 0.10,
    }


@app.route("/", methods=["GET", "POST"])
def beranda():
    komentar = ""
    pesan_error = None
    hasil = None

    if request.method == "POST":
        komentar = request.form.get("komentar", "")
        pesan_error = validasi_masukan(komentar)
        if not pesan_error:
            hasil = analisis_komentar(komentar)

    return render_template(
        "index.html",
        komentar=komentar,
        pesan_error=pesan_error,
        hasil=hasil,
        info=info_evaluasi,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8000)
