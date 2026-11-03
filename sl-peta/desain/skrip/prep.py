"""Bangun data.json untuk Peta Klub Super League.

Pemakaian (dari folder root proyek):
    python3 -I desain/skrip/prep.py

Masukan (semua di folder data/, boleh diedit di Excel/Google Sheets lalu disimpan sebagai CSV):
    data/meta.json          musim, catatan, daftar sumber
    data/klub.csv           satu baris per klub (profil + lokasi stadion)
    data/pemain_asing.csv   satu baris per pemain asing (club_id, pemain)
    data/nilai_pasar.csv    RIWAYAT nilai pasar: tambah baris baru tiap update (tanggal, club_id, nilai_rp_miliar, sumber)
    data/klasemen.csv       RIWAYAT klasemen: tambah 18 baris baru tiap pekan (pekan, tanggal, club_id, pos, ...)
    desain/indonesia-38-provinces.geojson  batas 38 provinsi

Keluaran: data.json di root proyek (dibaca main.js).
Skrip ini juga memeriksa data dan berhenti dengan pesan jelas kalau ada yang tidak cocok.
"""
import csv, json, math, os, sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)

LON0, LAT0, K = 95.0, 6.2, 1000 / 46.2      # proyeksi planar: x=(lon-95)*K, z=(6.2-lat)*K
EPS = 0.9                                     # toleransi penyederhanaan garis pantai (unit peta)
MIN_AREA = 6.0                                # pulau lebih kecil dari ini dibuang (unit peta^2)
NAME_FIX = {"Daerah Istimewa Yogyakarta": "DI Yogyakarta"}

errors, warnings = [], []


def proj(lon, lat):
    return ((lon - LON0) * K, (LAT0 - lat) * K)


def dp(pts, eps):
    """Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return dp(pts[:idx + 1], eps)[:-1] + dp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def area(r):
    return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2


def read_csv(name):
    with open(P("data", name), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(v, kind=float, where=""):
    try:
        return kind(str(v).strip().replace(",", ".")) if kind is float else kind(str(v).strip())
    except ValueError:
        errors.append(f"{where}: '{v}' bukan angka")
        return None


# ---------- geometri provinsi ----------
geo = json.load(open(P("desain", "indonesia-38-provinces.geojson"), encoding="utf-8"))
provinsi = []
for f in geo["features"]:
    nama = f["properties"]["PROVINSI"]
    nama = NAME_FIX.get(nama, nama)
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    rings, total, sx, sz = [], 0.0, 0.0, 0.0
    for poly in polys:
        outer = [proj(lon, lat) for lon, lat in poly[0]]
        a = area(outer)
        if a < MIN_AREA:
            continue
        m = len(outer) // 2
        simp = dp(outer[:m + 1], EPS)[:-1] + dp(outer[m:], EPS)
        if len(simp) > 2 and simp[0] == simp[-1]:
            simp = simp[:-1]
        if len(simp) < 3:
            continue
        rings.append(" ".join(f"{x:.1f},{z:.1f}" for x, z in simp))
        cx = sum(p[0] for p in outer) / len(outer)
        cz = sum(p[1] for p in outer) / len(outer)
        total += a; sx += cx * a; sz += cz * a
    if not rings:
        warnings.append(f"Provinsi {nama} tidak punya pulau yang cukup besar, dilewati")
        continue
    provinsi.append({"nama": nama, "kode": f["properties"].get("KODE_PROV"), "cx": round(sx / total, 1),
                     "cz": round(sz / total, 1), "rings": rings})
NAMA_PROV = {p["nama"] for p in provinsi}

# ---------- klub ----------
klub, ids = [], set()
for i, r in enumerate(read_csv("klub.csv"), start=2):
    w = f"klub.csv baris {i} ({r.get('id')})"
    cid = r["id"].strip()
    if not cid or cid in ids:
        errors.append(f"{w}: id kosong/duplikat")
    ids.add(cid)
    prov = NAME_FIX.get(r["province"].strip(), r["province"].strip())
    if prov not in NAMA_PROV:
        errors.append(f"{w}: provinsi '{prov}' tidak ada di peta. Pilihan: {', '.join(sorted(NAMA_PROV))}")
    lat, lon = num(r["lat"], float, w + " lat"), num(r["lon"], float, w + " lon")
    x, z = proj(lon, lat) if lat is not None and lon is not None else (0, 0)
    klub.append({
        "id": cid, "nama": r["club"].strip(), "pendek": r["short"].strip(), "kota": r["city"].strip(),
        "provinsi": prov, "stadion": r["stadium"].strip(), "kapasitas": num(r["capacity"], int, w + " capacity"),
        "x": round(x, 1), "z": round(z, 1), "pelatih": r["coach"].strip(), "kapten": r["captain"].strip(),
        "apparel": r["kit"].strip(), "status": r["status"].strip(), "musim_lalu": r["pos_2526"].strip(),
        "catatan": r["note"].strip(), "asing": [], "nilai": [], "klasemen": [],
    })
by_id = {k["id"]: k for k in klub}

for i, r in enumerate(read_csv("pemain_asing.csv"), start=2):
    k = by_id.get(r["club_id"].strip())
    if not k:
        errors.append(f"pemain_asing.csv baris {i}: club_id '{r['club_id']}' tidak dikenal")
        continue
    k["asing"].append(r["pemain"].strip())

for i, r in enumerate(read_csv("nilai_pasar.csv"), start=2):
    w = f"nilai_pasar.csv baris {i}"
    k = by_id.get(r["club_id"].strip())
    if not k:
        errors.append(f"{w}: club_id '{r['club_id']}' tidak dikenal")
        continue
    k["nilai"].append({"tanggal": r["tanggal"].strip(), "nilai": num(r["nilai_rp_miliar"], float, w),
                       "sumber": r["sumber"].strip()})

for i, r in enumerate(read_csv("klasemen.csv"), start=2):
    w = f"klasemen.csv baris {i}"
    k = by_id.get(r["club_id"].strip())
    if not k:
        errors.append(f"{w}: club_id '{r['club_id']}' tidak dikenal")
        continue
    row = {"pekan": num(r["pekan"], int, w), "tanggal": r["tanggal"].strip()}
    for f_ in ("pos", "main", "menang", "seri", "kalah", "poin"):
        row[f_] = num(r[f_], int, f"{w} {f_}")
    if None not in row.values():
        if row["menang"] + row["seri"] + row["kalah"] != row["main"]:
            errors.append(f"{w} ({k['id']}): menang+seri+kalah ≠ main")
        selisih = row["poin"] - (3 * row["menang"] + row["seri"])
        if selisih:
            warnings.append(f"{k['id']} pekan {row['pekan']}: poin selisih {selisih:+d} dari 3M+S (pengurangan poin?)")
    k["klasemen"].append(row)

for k in klub:
    k["nilai"].sort(key=lambda r: r["tanggal"])
    k["klasemen"].sort(key=lambda r: r["pekan"])
    if not k["nilai"]:
        warnings.append(f"{k['id']}: belum punya nilai pasar")
    if not k["klasemen"]:
        warnings.append(f"{k['id']}: belum punya data klasemen")

pekan = sorted({r["pekan"] for k in klub for r in k["klasemen"]})
if pekan:
    last = pekan[-1]
    hadir = [k["id"] for k in klub if any(r["pekan"] == last for r in k["klasemen"])]
    if len(hadir) != len(klub):
        warnings.append(f"Pekan {last} hanya punya {len(hadir)} dari {len(klub)} klub")
    posisi = sorted(r["pos"] for k in klub for r in k["klasemen"] if r["pekan"] == last)
    if posisi != list(range(1, len(posisi) + 1)):
        errors.append(f"Pekan {last}: urutan posisi tidak lengkap/duplikat {posisi}")

for w in warnings:
    print("PERINGATAN:", w)
if errors:
    for e in errors:
        print("GALAT:", e)
    sys.exit("data.json TIDAK dibuat. Perbaiki galat di atas lalu jalankan ulang.")

meta = json.load(open(P("data", "meta.json"), encoding="utf-8"))
last_k = [r for k in klub for r in k["klasemen"] if r["pekan"] == pekan[-1]] if pekan else []
meta.update({
    "pekan_terakhir": pekan[-1] if pekan else None,
    "tanggal_klasemen": max((r["tanggal"] for r in last_k), default=None),
    "tanggal_nilai": sorted({r["tanggal"] for k in klub for r in k["nilai"]}),
    "proyeksi": f"planar: x=(lon-{LON0})*{K:.4f}, z=({LAT0}-lat)*{K:.4f}",
})
out = {"meta": meta, "provinsi": provinsi, "klub": klub}
with open(P("data.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(f"OK: data.json ({os.path.getsize(P('data.json')) // 1024} KB) · {len(provinsi)} provinsi · {len(klub)} klub · "
      f"pekan {meta['pekan_terakhir']} · nilai pasar {', '.join(meta['tanggal_nilai'])}")
