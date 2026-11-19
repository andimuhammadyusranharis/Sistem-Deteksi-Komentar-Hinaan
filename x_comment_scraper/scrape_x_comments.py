"""Scraper komentar (balasan) tweet X/Twitter tanpa API berbayar.

Cara kerja: membuka tweet di Google Chrome lewat Playwright memakai sesi login
akun Anda sendiri, lalu membaca data balasan yang dimuat halaman saat di-scroll.

Contoh:
    python scrape_x_comments.py https://x.com/user/status/123456789 --max 100
    python scrape_x_comments.py --file urls.txt --max 50 --lang in --out hasil.csv
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE_DIR = HERE / "chrome_profile"  # menyimpan sesi login, jangan dibagikan

FIELDS = [
    "commentId", "tweetUrl", "twitterUsername", "twitterName", "isBlueVerified",
    "replyContent", "replyContentClean", "lang", "likeCount", "replyCount",
    "retweetCount", "quoteCount", "bookmarkCount", "viewCount", "createdAt",
]


def tweet_id_from_url(url):
    m = re.search(r"/status/(\d+)", url)
    if not m:
        raise ValueError(f"URL tweet tidak valid: {url}")
    return m.group(1)


def clean_text(text):
    """Samakan dengan konvensi dataset Ibrohim & Budi: mention -> USER, tautan -> URL."""
    text = re.sub(r"https?://\S+", "URL", text)
    text = re.sub(r"@\w+", "USER", text)
    return re.sub(r"\s+", " ", text).strip()


def iter_tweets(node):
    """Telusuri JSON secara rekursif dan hasilkan setiap objek tweet."""
    if isinstance(node, dict):
        result = node.get("tweet_results", {}).get("result") if "tweet_results" in node else None
        if isinstance(result, dict):
            if "tweet" in result:  # TweetWithVisibilityResults
                result = result["tweet"]
            if "legacy" in result:
                yield result
        for value in node.values():
            yield from iter_tweets(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_tweets(value)


def parse_reply(tweet, root_id, tweet_url):
    """Ubah objek tweet menjadi baris keluaran; None jika bukan balasan tweet target."""
    legacy = tweet["legacy"]
    tid = tweet.get("rest_id") or legacy.get("id_str")
    if not tid or tid == root_id or legacy.get("conversation_id_str") != root_id:
        return None

    user = (tweet.get("core", {}).get("user_results", {}).get("result") or {})
    user_core = user.get("core", {})
    user_legacy = user.get("legacy", {})

    note = (tweet.get("note_tweet", {}).get("note_tweet_results", {})
            .get("result", {}).get("text"))
    text = note or legacy.get("full_text", "")

    return {
        "commentId": tid,
        "tweetUrl": tweet_url,
        "twitterUsername": user_core.get("screen_name") or user_legacy.get("screen_name", ""),
        "twitterName": user_core.get("name") or user_legacy.get("name", ""),
        "isBlueVerified": bool(user.get("is_blue_verified")),
        "replyContent": text,
        "replyContentClean": clean_text(text),
        "lang": legacy.get("lang", ""),
        "likeCount": legacy.get("favorite_count", 0),
        "replyCount": legacy.get("reply_count", 0),
        "retweetCount": legacy.get("retweet_count", 0),
        "quoteCount": legacy.get("quote_count", 0),
        "bookmarkCount": legacy.get("bookmark_count", 0),
        "viewCount": tweet.get("views", {}).get("count", ""),
        "createdAt": legacy.get("created_at", ""),
    }


def ensure_login(context, page):
    def logged_in():
        return any(c["name"] == "auth_token" for c in context.cookies("https://x.com"))

    if logged_in():
        return
    page.goto("https://x.com/i/flow/login")
    print("Belum login. Silakan login ke X di jendela Chrome yang terbuka "
          "(menunggu maksimal 5 menit)...")
    deadline = time.time() + 300
    while time.time() < deadline:
        if logged_in():
            print("Login berhasil, sesi disimpan untuk pemakaian berikutnya.")
            page.wait_for_timeout(3000)
            return
        page.wait_for_timeout(2000)
    sys.exit("Login tidak terdeteksi dalam 5 menit. Jalankan ulang lalu coba lagi.")


def scrape_tweet(page, url, max_comments, lang):
    root_id = tweet_id_from_url(url)
    replies = {}

    def on_response(response):
        if "/TweetDetail" not in response.url:
            return
        try:
            data = response.json()
        except Exception:
            return
        for tweet in iter_tweets(data):
            row = parse_reply(tweet, root_id, url)
            if row and (not lang or row["lang"] == lang):
                replies.setdefault(row["commentId"], row)

    page.on("response", on_response)
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        stagnant = 0
        while len(replies) < max_comments and stagnant < 6:
            before = len(replies)
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(random.randint(1500, 3000))  # jeda agar tidak agresif
            stagnant = stagnant + 1 if len(replies) == before else 0
            print(f"\r  terkumpul {len(replies)} komentar", end="", flush=True)
        print()
    finally:
        page.remove_listener("response", on_response)
    return list(replies.values())[:max_comments]


# (judul kolom, kunci data, lebar kolom) untuk keluaran Excel
XLSX_COLUMNS = [
    ("No", None, 6),
    ("Username", "twitterUsername", 20),
    ("Nama", "twitterName", 22),
    ("Komentar", "replyContent", 70),
    ("Komentar (bersih)", "replyContentClean", 70),
    ("Like", "likeCount", 8),
    ("Balasan", "replyCount", 9),
    ("Retweet", "retweetCount", 9),
    ("Quote", "quoteCount", 8),
    ("Bookmark", "bookmarkCount", 10),
    ("Dilihat", "viewCount", 10),
    ("Waktu (WIB)", "createdAt", 18),
    ("Bahasa", "lang", 8),
    ("Centang Biru", "isBlueVerified", 12),
    ("ID Komentar", "commentId", 22),
    ("URL Tweet", "tweetUrl", 50),
]
NUMERIC_KEYS = {"likeCount", "replyCount", "retweetCount", "quoteCount", "bookmarkCount", "viewCount"}


def to_wib(created_at):
    """'Sun Dec 21 10:22:51 +0000 2025' -> datetime WIB (UTC+7); teks asli jika gagal."""
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        return dt.astimezone(timezone(timedelta(hours=7))).replace(tzinfo=None)
    except (ValueError, TypeError):
        return created_at


def save_xlsx(rows, out_path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Komentar"
    ws.append([title for title, _, _ in XLSX_COLUMNS])

    for no, row in enumerate(rows, 1):
        values = []
        for _, key, _ in XLSX_COLUMNS:
            value = no if key is None else row.get(key, "")
            if key in NUMERIC_KEYS:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = 0
            elif key == "createdAt":
                value = to_wib(value)
            elif key == "isBlueVerified":
                value = "Ya" if str(value) == "True" else "Tidak"
            elif key == "commentId":
                value = str(value)  # teks, agar ID 19 digit tidak dibulatkan Excel
            values.append(value)
        ws.append(values)

    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap_keys = {"replyContent", "replyContentClean"}
    for col, (_, key, width) in enumerate(XLSX_COLUMNS, 1):
        letter = get_column_letter(col)
        ws.column_dimensions[letter].width = width
        head = ws.cell(row=1, column=col)
        head.font = Font(bold=True, color="FFFFFF")
        head.fill = PatternFill("solid", fgColor="1F4E78")
        head.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        head.border = border
        for r in range(2, ws.max_row + 1):
            cell = ws.cell(row=r, column=col)
            cell.border = border
            if key in wrap_keys:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            elif key in NUMERIC_KEYS:
                cell.alignment = Alignment(horizontal="right", vertical="top")
                cell.number_format = "#,##0"
            elif key in ("twitterUsername", "twitterName", "tweetUrl"):
                cell.alignment = Alignment(vertical="top")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="top")
            if key == "createdAt":
                cell.number_format = "dd/mm/yyyy hh:mm"
            elif key == "commentId":
                cell.number_format = "@"

    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "D2"  # judul, No, Username, Nama tetap terlihat saat digulir
    ws.auto_filter.ref = ws.dimensions
    wb.save(out_path)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save(rows, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".xlsx":
        save_xlsx(rows, out_path)
    elif out_path.suffix.lower() == ".json":
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        # utf-8-sig agar emoji/aksara tampil benar saat dibuka di Excel
        with out_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Scraper komentar tweet X/Twitter")
    ap.add_argument("urls", nargs="*", help="URL tweet (boleh lebih dari satu)")
    ap.add_argument("--file", help="berkas teks berisi URL tweet, satu per baris")
    ap.add_argument("--max", type=int, default=100, help="maks. komentar per tweet (default 100)")
    ap.add_argument("--lang", default="", help="saring bahasa, mis. 'in' untuk Indonesia")
    ap.add_argument("--out", default="komentar.csv", help="berkas keluaran .csv, .xlsx, atau .json")
    ap.add_argument("--convert", metavar="CSV",
                    help="ubah berkas CSV hasil sebelumnya menjadi --out tanpa scraping ulang")
    args = ap.parse_args()

    if args.convert:
        rows = read_csv(args.convert)
        out_path = Path(args.out if args.out != "komentar.csv" else
                        Path(args.convert).with_suffix(".xlsx"))
        save(rows, out_path)
        print(f"Selesai: {len(rows)} komentar disimpan ke {out_path.resolve()}")
        return

    urls = list(args.urls)
    if args.file:
        for line in Path(args.file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    if not urls:
        ap.error("berikan minimal satu URL tweet atau --file")
    for u in urls:
        tweet_id_from_url(u)

    from playwright.sync_api import sync_playwright

    all_rows = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        ensure_login(context, page)
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url}")
            try:
                all_rows.extend(scrape_tweet(page, url, args.max, args.lang))
            except Exception as e:
                print(f"  gagal: {e}")
            if i < len(urls):
                page.wait_for_timeout(random.randint(4000, 8000))
        context.close()

    out_path = Path(args.out)
    save(all_rows, out_path)
    print(f"Selesai: {len(all_rows)} komentar disimpan ke {out_path.resolve()}")


if __name__ == "__main__":
    main()
