"""
toilet_api.py
-------------
FastAPI router — tuvalet endpoint'leri.

api.py'ye eklemek için:
    from toilet_api import router as tuvalet_router
    app.include_router(tuvalet_router)
"""

import sqlite3
import math
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

DB_DOSYASI = "smartexit.db"


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def kus_ucusu_mesafe(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formülü — iki koordinat arası metre cinsinden mesafe."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def db_baglan() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_DOSYASI)
    conn.row_factory = sqlite3.Row
    return conn


def tuvalet_tablosu_var_mi(cursor: sqlite3.Cursor) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tuvaletler'"
    )
    return cursor.fetchone() is not None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/api/v1/tuvaletler")
async def tuvaletleri_getir(
    lat: float = Query(..., description="Kullanıcı enlemi"),
    lon: float = Query(..., description="Kullanıcı boylamı"),
    yaricap: int = Query(1000, ge=100, le=5000, description="Arama yarıçapı (metre)"),
    sadece_ucretsiz: bool = Query(False, description="Sadece ücretsiz tuvaletler"),
    sadece_engelli: bool = Query(False, description="Sadece engelli erişimli"),
):
    """
    Kullanıcının konumuna yakın tuvaletleri döndürür.
    Mesafeye göre sıralı, en yakın önce gelir.
    """

    # Koordinat doğrulama
    if math.isnan(lat) or math.isnan(lon):
        raise HTTPException(status_code=400, detail="Geçersiz koordinat.")
    if not (40.7 <= lat <= 41.6 and 27.9 <= lon <= 29.9):
        raise HTTPException(status_code=400, detail="Koordinat İstanbul sınırları dışında.")

    try:
        conn   = db_baglan()
        cursor = conn.cursor()

        if not tuvalet_tablosu_var_mi(cursor):
            conn.close()
            raise HTTPException(
                status_code=503,
                detail="Tuvalet veritabanı henüz oluşturulmamış. "
                       "Lütfen toilet_db_builder.py dosyasını çalıştırın."
            )

        # Tüm tuvaletleri çek (maks ~440 kayıt — anlık filtre)
        sorgu = "SELECT * FROM tuvaletler WHERE enlem IS NOT NULL AND boylam IS NOT NULL"
        params = []

        if sadece_ucretsiz:
            sorgu += " AND ucretli = 0"
        if sadece_engelli:
            sorgu += " AND engelli_erisimi = 1"

        cursor.execute(sorgu, params)
        rows = cursor.fetchall()
        conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veritabanı hatası: {str(e)}")

    # Python tarafında mesafe hesapla ve filtrele
    sonuclar = []
    for row in rows:
        t_lat = row["enlem"]
        t_lon = row["boylam"]

        # NaN koruması
        if t_lat != t_lat or t_lon != t_lon:
            continue

        mesafe = kus_ucusu_mesafe(lat, lon, t_lat, t_lon)

        if mesafe > yaricap:
            continue

        sonuclar.append({
            "id":              row["id"],
            "osm_id":          row["osm_id"],
            "enlem":           t_lat,
            "boylam":          t_lon,
            "ad":              row["ad"],
            "ucretli":         bool(row["ucretli"]),
            "ucret_miktari":   row["ucret_miktari"],
            "acilis_kapanis":  row["acilis_kapanis"],
            "engelli_erisimi": bool(row["engelli_erisimi"]),
            "bebek_bakim":     bool(row["bebek_bakim"]),
            "erisim_tipi":     row["erisim_tipi"],
            "istanbulkart":    bool(row["istanbulkart"]),
            "kadinlar":        bool(row["kadinlar"]),
            "erkekler":        bool(row["erkekler"]),
            "unisex":          bool(row["unisex"]),
            "mesafe_metre":    round(mesafe),
        })

    # Mesafeye göre sırala
    sonuclar.sort(key=lambda x: x["mesafe_metre"])

    return {
        "durum":   "basarili",
        "toplam":  len(sonuclar),
        "yaricap": yaricap,
        "tuvaletler": sonuclar,
    }


@router.get("/api/v1/tuvaletler/{tuvalet_id}")
async def tuvalet_detay(tuvalet_id: int):
    """Tek bir tuvaleti ID ile getirir."""
    try:
        conn   = db_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tuvaletler WHERE id = ?", (tuvalet_id,))
        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veritabanı hatası: {str(e)}")

    if row is None:
        raise HTTPException(status_code=404, detail="Tuvalet bulunamadı.")

    return {
        "id":              row["id"],
        "osm_id":          row["osm_id"],
        "enlem":           row["enlem"],
        "boylam":          row["boylam"],
        "ad":              row["ad"],
        "ucretli":         bool(row["ucretli"]),
        "ucret_miktari":   row["ucret_miktari"],
        "acilis_kapanis":  row["acilis_kapanis"],
        "engelli_erisimi": bool(row["engelli_erisimi"]),
        "bebek_bakim":     bool(row["bebek_bakim"]),
        "erisim_tipi":     row["erisim_tipi"],
        "istanbulkart":    bool(row["istanbulkart"]),
        "kadinlar":        bool(row["kadinlar"]),
        "erkekler":        bool(row["erkekler"]),
        "unisex":          bool(row["unisex"]),
    }
