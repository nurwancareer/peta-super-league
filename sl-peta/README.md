# Peta Klub Super League

Peta isometrik 3D 18 klub BRI Super League 2026/27. Tinggi tiap provinsi mengikuti lensa yang dipilih (nilai pasar, poin, jumlah klub, kapasitas stadion). Klik provinsi untuk melihat klub-klubnya, klik tiang stadion untuk profil klub.

Tautan langsung: `.../#persib` (klub, pakai `id` dari `data/klub.csv`) atau `.../#Jawa%20Timur` (provinsi).

## Struktur

```
index.html            kerangka halaman: <canvas> 3D + kartu HTML di atasnya
gaya.css              tampilan
main.js               peta 3D (Three.js), kamera, hover, klik, panel detail, lensa
data.json             DIBUAT OTOMATIS oleh prep.py, jangan diedit manual
vendor/three/         Three.js 0.187 (disimpan lokal, tanpa CDN)
data/                 ← DATA MENTAH, yang kamu update
  meta.json           musim, catatan, daftar sumber (tampil di footer)
  klub.csv            profil klub: stadion, koordinat, pelatih, kapten, apparel, dll.
  pemain_asing.csv    satu baris per pemain asing
  nilai_pasar.csv     RIWAYAT nilai pasar (tambah baris, jangan timpa)
  klasemen.csv        RIWAYAT klasemen per pekan (tambah 18 baris tiap pekan)
desain/
  indonesia-38-provinces.geojson   batas provinsi (CC BY 4.0)
  skrip/prep.py       CSV + GeoJSON → data.json, sekaligus memeriksa data
```

## Menjalankan lokal

```sh
python3 desain/skrip/prep.py      # bangun ulang data.json
python3 -m http.server 8000       # lalu buka http://localhost:8000
```

Harus lewat server, bukan klik ganda `index.html`, karena `data.json` dimuat dengan `fetch`.

## Update berkala

**Klasemen (tiap pekan)**: buka `data/klasemen.csv`, tambahkan 18 baris baru dengan `pekan` dan `tanggal` baru. Baris lama jangan dihapus; itu yang mengisi grafik "Posisi per pekan" di profil klub.

```
pekan,tanggal,club_id,pos,main,menang,seri,kalah,poin
9,2026-11-08,persija,1,9,7,0,2,21
```

**Nilai pasar (kapan saja)**: tambahkan baris di `data/nilai_pasar.csv` dengan tanggal baru. Lensa "Nilai pasar" di peta otomatis memakai tanggal terbaru yang lengkap untuk ke-18 klub, jadi semua provinsi dibandingkan pada tanggal yang sama. Profil klub tetap menampilkan riwayat lengkapnya.

**Pergantian pelatih, kapten, stadion, pemain asing**: edit `data/klub.csv` atau `data/pemain_asing.csv`.

**Musim baru / klub promosi**: tambahkan klub di `klub.csv` dengan `id` baru (huruf kecil, tanpa spasi). `province` harus persis salah satu nama provinsi di peta; kalau salah, prep.py akan menampilkan daftar nama yang valid.

Setelah mengedit, jalankan `python3 desain/skrip/prep.py`. Skrip akan:
- berhenti dengan pesan `GALAT` kalau ada `club_id` yang tidak dikenal, nama provinsi salah, angka tidak valid, `menang+seri+kalah ≠ main`, atau urutan posisi bolong/dobel;
- memberi `PERINGATAN` (tidak berhenti) kalau poin ≠ 3×menang+seri, misalnya karena pengurangan poin.

Kalau repo ini di GitHub, workflow di `.github/workflows/data.yml` menjalankan prep.py otomatis setiap kali file di `data/` berubah, lalu meng-commit `data.json` yang baru. Jadi CSV bisa diedit langsung dari situs GitHub.

## GitHub Pages

Settings → Pages → Deploy from branch → `main` → `/ (root)`.

## Sumber data (edisi awal)

- Klasemen pekan 8 (1 Nov 2026): ANTARA
- Nilai pasar: Transfermarkt via Murianews (31 Agt 2026) dan Databoks (2 Okt 2026, hanya 10 besar)
- Stadion, kapasitas, pelatih, kapten, apparel, pemain asing: Wikipedia (2026–27 Super League) & I.League
- Koordinat stadion: perkiraan koordinat kota stadion
- Batas provinsi: denyherianto/indonesia-geojson-topojson-maps-with-38-provinces (CC BY 4.0), disederhanakan Douglas-Peucker
