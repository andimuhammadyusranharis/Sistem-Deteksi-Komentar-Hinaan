"""Buat berkas pelabelan (Excel) dari CSV hasil scrape_x_comments.py.

Identitas penulis (username, nama, ID komentar) tidak disertakan. Kolom No
mengikuti urutan baris pada CSV sumber sehingga hasil label tetap bisa dicocokkan.

Contoh:
    python buat_berkas_label.py komentar.csv
    python buat_berkas_label.py komentar.csv --out pelabelan_uji.xlsx
"""

import argparse
import csv
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

HEADERS = [("No", 6), ("Komentar", 90), ("Jumlah kata", 9), ("Pelabel 1", 11),
           ("Pelabel 2", 11), ("Label akhir", 11), ("Catatan", 40)]

PANDUAN = [
    ("Panduan pengisian", True),
    ("Data: komentar publik dari X sebagai data uji tambahan (bukan data simulasi, bukan data latih).", False),
    ("", False),
    ("Arti label", True),
    ("1 = menghina: komentar memuat kata kasar/makian ATAU ujaran kebencian (menyerang orang atau "
     "kelompok), walaupun tanpa kata kasar. Ini mengikuti aturan label data latih: Abusive = 1 atau HS = 1.", False),
    ("0 = bukan menghina: selain itu, termasuk kritik tanpa hinaan, komentar netral, dan topik lain. "
     "Bukan menghina tidak berarti konstruktif.", False),
    ("", False),
    ("Cara mengisi", True),
    ("1. Tiap pelabel mengisi kolomnya sendiri (Pelabel 1 atau Pelabel 2) dengan 0 atau 1, tanpa melihat isian pelabel lain.", False),
    ("2. Nilai yang dinilai adalah isi komentar, bukan sikap politiknya dan bukan benar-salahnya.", False),
    ("3. Kolom Label akhir terisi otomatis jika kedua pelabel sepakat. Jika tertulis BEDA, diskusikan, "
     "lalu ketik label yang disepakati di kolom Label akhir dan tulis alasannya di Catatan.", False),
    ("4. Kasus sulit (sarkasme, kata kasar yang tidak menyerang siapa pun) dicatat di kolom Catatan untuk analisis kesalahan.", False),
    ("5. Jumlah kata dihitung tanpa penanda USER/URL. Aplikasi menolak masukan kurang dari 3 kata, "
     "jadi baris seperti itu tetap dilabeli tetapi dilaporkan terpisah.", False),
    ("", False),
    ("Panduan ini adalah draf awal; lengkapi dengan contoh dari kelompok sebelum pelabelan dimulai.", False),
]


def word_count(text):
    return len(re.sub(r"\b(USER|URL)\b", " ", text).split())


def main():
    ap = argparse.ArgumentParser(description="Buat berkas pelabelan dari CSV komentar")
    ap.add_argument("csv_path", help="CSV hasil scrape_x_comments.py")
    ap.add_argument("--out", help="berkas keluaran .xlsx (default: pelabelan_<nama csv>.xlsx)")
    args = ap.parse_args()

    src = Path(args.csv_path)
    out = Path(args.out) if args.out else src.with_name(f"pelabelan_{src.stem}.xlsx")
    if out.exists():
        raise SystemExit(f"{out} sudah ada. Hapus/ganti namanya dulu agar label yang sudah diisi tidak tertimpa.")
    with src.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    wb = Workbook()
    ws = wb.active
    ws.title = "Pelabelan"
    ws.append([h for h, _ in HEADERS])
    for no, row in enumerate(rows, 1):
        r = no + 1
        text = row["replyContentClean"]
        ws.append([no, text, word_count(text), None, None,
                   f'=IF(OR(D{r}="",E{r}=""),"",IF(D{r}=E{r},D{r},"BEDA"))', None])

    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    last = ws.max_row
    for col, (_, width) in enumerate(HEADERS, 1):
        letter = ws.cell(row=1, column=col).column_letter
        ws.column_dimensions[letter].width = width
        head = ws.cell(row=1, column=col)
        head.font = Font(bold=True, color="FFFFFF")
        head.fill = PatternFill("solid", fgColor="1F4E78")
        head.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        head.border = border
        for r in range(2, last + 1):
            cell = ws.cell(row=r, column=col)
            cell.border = border
            wrap = letter in ("B", "G")
            cell.alignment = Alignment(vertical="top", wrap_text=wrap,
                                       horizontal=None if wrap else "center")
            if letter in ("D", "E"):
                cell.fill = PatternFill("solid", fgColor="FFF2CC")  # sel yang diisi pelabel

    dv = DataValidation(type="list", formula1='"0,1"', allow_blank=True,
                        errorTitle="Label tidak valid", error="Isi dengan 0 atau 1.")
    ws.add_data_validation(dv)
    dv.add(f"D2:E{last}")
    ws.conditional_formatting.add(
        f"F2:F{last}",
        CellIsRule(operator="equal", formula=['"BEDA"'],
                   fill=PatternFill("solid", bgColor="F8CBAD"), font=Font(bold=True, color="C00000")))
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:G{last}"

    wp = wb.create_sheet("Panduan")
    wp.column_dimensions["A"].width = 120
    for text, bold in PANDUAN:
        wp.append([text])
        cell = wp.cell(row=wp.max_row, column=1)
        cell.font = Font(bold=bold)
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(out)
    short = sum(1 for row in rows if word_count(row["replyContentClean"]) < 3)
    print(f"Selesai: {len(rows)} komentar ({short} di antaranya kurang dari 3 kata) -> {out.resolve()}")


if __name__ == "__main__":
    main()
