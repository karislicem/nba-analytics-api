# NBA Advanced Analytics API
# Render.com Deployment

## 🚀 Hızlı Deploy (5 dakika)

### 1. GitHub Repo Oluştur
- GitHub'da yeni repo aç: `nba-analytics-api`
- Bu klasördeki dosyaları yükle

### 2. Render.com'a Git
- https://render.com adresine git
- GitHub ile giriş yap
- "New +" → "Web Service" seç
- GitHub reposunu bağla

### 3. Ayarlar
```
Name: nba-analytics-api
Region: Oregon (US West)
Branch: main
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn nba_api_backend_v4:app --bind 0.0.0.0:$PORT
Instance Type: Free
```

### 4. Deploy!
- "Create Web Service" tıkla
- 2-3 dakika bekle
- URL'ini al: `https://nba-analytics-api.onrender.com`

---

## 📁 Gerekli Dosyalar

```
nba-analytics-api/
├── nba_api_backend_v4.py   # Ana API dosyası
├── requirements.txt         # Python bağımlılıkları
├── render.yaml             # Render config (opsiyonel)
└── README.md               # Bu dosya
```

---

## ⚠️ Önemli Notlar

### Free Tier Limitleri
- 750 saat/ay (yeterli)
- 15 dakika inaktivite → sleep mode
- İlk istek 30-50sn sürebilir (cold start)

### Sleep Mode Çözümü
UptimeRobot.com ile her 14 dakikada ping atabilirsin (ücretsiz):
1. https://uptimerobot.com kayıt ol
2. "Add New Monitor" → HTTP(s)
3. URL: `https://nba-analytics-api.onrender.com/api/season`
4. Interval: 5 minutes

---

## 🔧 Frontend Güncelleme

Dashboard HTML'de API URL'ini güncelle:

```javascript
// Eskisi
const API_BASE = 'http://localhost:5000';

// Yenisi
const API_BASE = 'https://nba-analytics-api.onrender.com';
```

---

## 🧪 Test

Deploy sonrası test et:
```bash
curl https://nba-analytics-api.onrender.com/api/advanced/LAL/BOS
```
