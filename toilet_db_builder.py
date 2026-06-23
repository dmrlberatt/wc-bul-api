"""
toilet_db_builder.py
--------------------
Mevcut GeoJSON dosyasından (toilets.geojson) tuvalet verilerini okur
ve smartexit.db'ye "tuvaletler" tablosu olarak yazar.

Kullanım:
    python toilet_db_builder.py

Bir kez çalıştırılır. Tekrar çalıştırılırsa tablo sıfırlanıp yeniden yazılır.
"""

import json
import sqlite3
import os

GEOJSON_DOSYASI = "toilets.geojson"
DB_DOSYASI      = "smartexit.db"


def polygon_centroid(koordinatlar: list) -> tuple:
    """
    Polygon'un centroid'ini hesaplar.
    GeoJSON koordinatları [boylam, enlem] sırasındadır.
    Dış ring'i (koordinatlar[0]) alıp ortalamasını hesaplarız.
    """
    dis_ring = koordinatlar[0]
    lon = sum(p[0] for p in dis_ring) / len(dis_ring)
    lat = sum(p[1] for p in dis_ring) / len(dis_ring)
    return lat, lon


def koordinat_al(feature: dict):
    """
    Feature'dan (enlem, boylam) çıkarır.
    Point  → direkt koordinat
    Polygon → centroid
    Diğer   → None (atla)
    """
    geo      = feature["geometry"]
    geo_type = geo["type"]

    if geo_type == "Point":
        lon, lat = geo["coordinates"]
        return lat, lon
    elif geo_type == "Polygon":
        return polygon_centroid(geo["coordinates"])
    return None


def bool_al(deger) -> int:
    """'yes'/'no' string'ini 0/1 integer'a çevirir."""
    return 1 if str(deger).strip().lower() == "yes" else 0


def tablo_olustur(cursor: sqlite3.Cursor):
    cursor.execute("DROP TABLE IF EXISTS tuvaletler")
    cursor.execute("""
        CREATE TABLE tuvaletler (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id          TEXT,
            enlem           REAL NOT NULL,
            boylam          REAL NOT NULL,
            ad              TEXT,
            ucretli         INTEGER DEFAULT 0,
            ucret_miktari   TEXT,
            acilis_kapanis  TEXT,
            engelli_erisimi INTEGER DEFAULT 0,
            bebek_bakim     INTEGER DEFAULT 0,
            erisim_tipi     TEXT,
            istanbulkart    INTEGER DEFAULT 0,
            kadinlar        INTEGER DEFAULT 0,
            erkekler        INTEGER DEFAULT 0,
            unisex          INTEGER DEFAULT 0
        )
    """)


def veri_yukle(cursor: sqlite3.Cursor, features: list) -> tuple:
    eklenen = 0
    atlanan = 0

    for feature in features:
        props = feature.get("properties", {})

        # Sadece amenity=toilets olanları al
        # (GeoJSON'da benzin istasyonu gibi dolaylı kayıtlar da var)
        if props.get("amenity") != "toilets":
            atlanan += 1
            continue

        koord = koordinat_al(feature)
        if koord is None:
            atlanan += 1
            continue

        lat, lon = koord

        # NaN / sıfır koordinat koruması
        if not lat or not lon or lat != lat or lon != lon:
            atlanan += 1
            continue

        # İstanbul kaba sınır filtresi
        if not (40.7 <= lat <= 41.6 and 27.9 <= lon <= 29.9):
            atlanan += 1
            continue

        cursor.execute("""
            INSERT INTO tuvaletler
                (osm_id, enlem, boylam, ad, ucretli, ucret_miktari,
                 acilis_kapanis, engelli_erisimi, bebek_bakim, erisim_tipi,
                 istanbulkart, kadinlar, erkekler, unisex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            props.get("@id", ""),
            lat, lon,
            props.get("name") or None,
            bool_al(props.get("fee")),
            props.get("charge") or None,
            props.get("opening_hours") or None,
            bool_al(props.get("wheelchair") or props.get("toilets:wheelchair")),
            bool_al(props.get("changing_table")),
            props.get("access") or None,
            bool_al(props.get("payment:istanbulkart")),
            bool_al(props.get("female")),
            bool_al(props.get("male")),
            bool_al(props.get("unisex")),
        ))
        eklenen += 1

    return eklenen, atlanan


def main():
    if not os.path.exists(GEOJSON_DOSYASI):
        print(f"HATA: '{GEOJSON_DOSYASI}' bulunamadi.")
        print("Bu scripti GeoJSON dosyasiyla ayni klasorde calistir.")
        return

    print(f"'{GEOJSON_DOSYASI}' okunuyor...")
    with open(GEOJSON_DOSYASI, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"Toplam {len(features)} feature bulundu.")

    conn   = sqlite3.connect(DB_DOSYASI)
    cursor = conn.cursor()

    print("Tablo olusturuluyor...")
    tablo_olustur(cursor)

    print("Veriler yaziliyor...")
    eklenen, atlanan = veri_yukle(cursor, features)

    conn.commit()
    conn.close()

    print("-" * 40)
    print(f"Eklenen : {eklenen} tuvalet")
    print(f"Atlanan : {atlanan} kayit (amenity!=toilets veya gecersiz koordinat)")
    print(f"Veritabani: '{DB_DOSYASI}' -> 'tuvaletler' tablosu hazir.")


if __name__ == "__main__":
    main()
