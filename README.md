# Banko Bot

Telegram için admin-only banko analiz botu. Celery + Redis ile batch analiz, Monte‑Carlo simülasyonu ve Telegram entegrasyonu içerir.

## Özet
- Sadece `ADMIN_ID` ile komut çalışır.
- `/start`, `/banko`, `/dur` komutları.
- Redis `requests_queue` üzerinden 150k istek işlenebilir.
- Analiz: ön-hesaplı lambda + Monte‑Carlo + ensemble.

## Dosyalar
- `bot.py` — Telegram bot
- `analysis.py` — analiz fonksiyonları
- `worker.py` — Celery task
- `Dockerfile`, `docker-compose.yml`
- `.env.example` — ortam değişkenleri şablonu

## Kurulum (local)
1. `.env` dosyasını oluşturun (örnek: `.env.example`).
2. `docker-compose up --build`
3. Telegram ile `/start`, `/banko` test edin.

## Güvenlik
- **.env** veya tokenleri repo’ya commit etmeyin.
- GitHub Secrets veya Railway secrets kullanın.
