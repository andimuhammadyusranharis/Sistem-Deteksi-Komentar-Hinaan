import re
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report


# 1. Fungsi untuk membaca kamus kata gaul (alay) dan daftar kata kasar
def muat_kamus():
    # new_kamusalay.csv berisi 2 kolom tanpa header: [kata_gaul, kata_baku]
    df_alay = pd.read_csv("new_kamusalay.csv", encoding="latin-1", header=None)
    kamus_alay = dict(zip(df_alay[0], df_alay[1]))

    # abusive.csv berisi 1 kolom daftar kata kasar
    df_kasar = pd.read_csv("abusive.csv", encoding="latin-1")
    daftar_kasar = set(df_kasar["ABUSIVE"].str.lower().str.strip())

    return kamus_alay, daftar_kasar


# 2. Fungsi praproses teks komentar
def bersihkan_teks(teks, kamus_alay):
    # Ubah ke huruf kecil semua
    teks = str(teks).lower()

    # Hapus kata penanda bawaan dataset: user, url, rt
    teks = re.sub(r"\b(user|url|rt)\b", " ", teks)

    # Kurangi huruf berulang 3 kali atau lebih (contoh: "tololll" -> "tolol")
    teks = re.sub(r"(.)\1{2,}", r"\1", teks)

    # Hapus simbol dan tanda baca (sisakan huruf dan angka)
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)

    # Ganti kata gaul menjadi kata baku menggunakan kamus
    kata_kata = teks.split()
    kata_baku = [kamus_alay.get(k, k) for k in kata_kata]

    return " ".join(kata_baku)


# 3. Proses utama pelatihan model JST
if __name__ == "__main__":
    print("1. Memuat dataset dan kamus...")
    kamus_alay, daftar_kasar = muat_kamus()
    df = pd.read_csv("re_dataset.csv", encoding="latin-1")
    jumlah_awal = len(df)

    # Buat label biner: 1 (Menghina) jika Abusive=1 atau HS=1, selain itu 0 (Bukan Menghina)
    df["label"] = ((df["Abusive"] == 1) | (df["HS"] == 1)).astype(int)

    print("2. Melakukan praproses teks...")
    df["teks_bersih"] = df["Tweet"].apply(lambda t: bersihkan_teks(t, kamus_alay))

    # Hapus teks kembar (duplikat) setelah praproses
    df = df.drop_duplicates(subset=["teks_bersih"]).reset_index(drop=True)
    jumlah_bersih = len(df)
    jumlah_duplikat = jumlah_awal - jumlah_bersih

    print(f"   - Data awal         : {jumlah_awal}")
    print(f"   - Duplikat dihapus  : {jumlah_duplikat}")
    print(f"   - Data bersih       : {jumlah_bersih}")

    # 4. Bagi data menjadi 80% data latih dan 20% data uji (berstrata)
    X_latih_teks, X_uji_teks, y_latih, y_uji = train_test_split(
        df["teks_bersih"],
        df["label"],
        test_size=0.20,
        random_state=42,
        stratify=df["label"],
    )

    # 5. Ubah teks menjadi angka dengan TF-IDF (maksimal 3.000 kata)
    print("3. Mengubah teks menjadi vektor angka (TF-IDF 3.000 fitur)...")
    tfidf = TfidfVectorizer(max_features=3000)
    X_latih = tfidf.fit_transform(X_latih_teks)
    X_uji = tfidf.transform(X_uji_teks)

    # 6. Bangun dan latih Jaringan Syaraf Tiruan (MLPClassifier)
    # 1 hidden layer berisi 16 neuron, fungsi aktivasi sigmoid ('logistic')
    print("4. Melatih Jaringan Syaraf Tiruan (1 hidden layer, 16 neuron, sigmoid)...")
    jst = MLPClassifier(
        hidden_layer_sizes=(16,),
        activation="logistic",
        max_iter=200,
        early_stopping=True,
        random_state=42,
    )
    jst.fit(X_latih, y_latih)

    # 7. Evaluasi model pada data uji
    y_pred = jst.predict(X_uji)
    akurasi = accuracy_score(y_uji, y_pred)
    # Baseline: jika selalu menebak kelas yang paling banyak (Menghina = 1)
    baseline = y_uji.value_counts(normalize=True).max()
    cm = confusion_matrix(y_uji, y_pred)

    print("\n=== HASIL EVALUASI DATA UJI ===")
    print(f"Jumlah data uji  : {len(y_uji)}")
    print(f"Akurasi Baseline : {baseline * 100:.1f}%")
    print(f"Akurasi JST      : {akurasi * 100:.1f}%")
    print("\nConfusion Matrix (Baris = Label Sebenarnya, Kolom = Prediksi):")
    print(cm)
    print("\nClassification Report:")
    print(classification_report(y_uji, y_pred, target_names=["Bukan Menghina (0)", "Menghina (1)"]))

    # 8. Simpan model, TF-IDF, kamus, dan ringkasan evaluasi ke satu file
    paket_model = {
        "jst": jst,
        "tfidf": tfidf,
        "kamus_alay": kamus_alay,
        "daftar_kasar": daftar_kasar,
        "info_evaluasi": {
            "data_awal": jumlah_awal,
            "duplikat_dihapus": jumlah_duplikat,
            "data_bersih": jumlah_bersih,
            "jumlah_uji": len(y_uji),
            "akurasi": round(akurasi * 100, 1),
            "baseline": round(baseline * 100, 1),
            "tn": int(cm[0][0]),
            "fp": int(cm[0][1]),
            "fn": int(cm[1][0]),
            "tp": int(cm[1][1]),
        },
    }
    joblib.dump(paket_model, "model_jst.joblib")
    print("5. Model berhasil disimpan ke berkas 'model_jst.joblib'.")
