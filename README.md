# WC Bul — Backend

İstanbul tuvalet verilerini sunan FastAPI servisi.

## Kurulum (VPS)

```bash
# 1. Repoyu çek
git clone https://github.com/kullanici/wcbul-backend.git
cd wcbul-backend

# 2. Venv oluştur ve aktif et
python3 -m venv venv
source venv/bin/activate

# 3. Paketleri kur
pip install -r requirements.txt

# 4. Veritabanını oluştur (sadece bir kez)
python toilet_db_builder.py

# 5. Servisi başlat
uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```

## Endpoint'ler

### Yakın tuvaletleri listele
```
GET /api/v1/tuvaletler?lat=41.01&lon=28.97&yaricap=1000
```

Parametreler:
- `lat` — kullanıcı enlemi (zorunlu)
- `lon` — kullanıcı boylamı (zorunlu)
- `yaricap` — metre cinsinden arama yarıçapı (varsayılan: 1000, max: 5000)
- `sadece_ucretsiz` — true/false (varsayılan: false)
- `sadece_engelli` — true/false (varsayılan: false)

Örnek cevap:
```json
{
  "durum": "basarili",
  "toplam": 3,
  "yaricap": 1000,
  "tuvaletler": [
    {
      "id": 12,
      "enlem": 41.012,
      "boylam": 28.974,
      "ad": null,
      "ucretli": false,
      "ucret_miktari": null,
      "acilis_kapanis": "08:00-22:00",
      "engelli_erisimi": true,
      "bebek_bakim": false,
      "erisim_tipi": "public",
      "istanbulkart": false,
      "kadinlar": true,
      "erkekler": true,
      "unisex": false,
      "mesafe_metre": 342
    }
  ]
}
```

### Tek tuvalet detayı
```
GET /api/v1/tuvaletler/{id}
```

## Repo Yapısı

```
wcbul-backend/
├── api.py                  ← FastAPI uygulaması (port 8001)
├── toilet_api.py           ← Endpoint router
├── toilet_db_builder.py    ← GeoJSON → SQLite (bir kez çalıştır)
├── export_15_.geojson      ← İstanbul tuvalet verisi
├── requirements.txt
└── README.md
```

## Notlar

- Veritabanı (`wcbul.db`) `.gitignore`'a eklenir, repoya gitmez.
- `toilet_db_builder.py` her çalıştırıldığında tabloyu sıfırdan yazar.
- ExIST API port 8000'de çalışır, bu servis 8001'de — çakışmaz.
