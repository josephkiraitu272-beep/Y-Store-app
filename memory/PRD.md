# PRD — Y-Store Telegram Mini App

## Original Problem Statement
Разверни данный проект из репозитория https://github.com/svetlanaslinko057/dedede2333
Изучи структуру, архитектуру, интеграцию Нової Пошти и платежной системы WayForPay.
Затем продолжим доработку миниапки.

## Architecture
- **Backend**: FastAPI (Python 3.11) + MongoDB (Motor) — `/app/backend`
  - Entry: `server.py` 
  - Core: `core/` (db, config, models, security)
  - Routers: `modules/tma/routes.py` (main TMA API), `modules/shop_routes.py`, `modules/seed_routes.py`, `modules/telegram_bff.py`, `modules/tma/nova_poshta_routes.py`
  - Auto-seed of categories + products on startup
  - Sandbox auth enabled via `TMA_ALLOW_SANDBOX=1` for browser testing without Telegram
- **Frontend**: React 19 (CRA + craco) — `/app/frontend`
  - TMA mobile-first client: `src/tma-mobile/` mounted at route `/tma/*`
  - Web storefront: `src/` mounted at `/`
- **DB**: MongoDB `tma_store` (local) — indexes auto-created on startup
- **Telegram Bot**: `@Ystore_app_bot` (id `8524617770`) — polling under supervisor

## Integrations
- **Telegram Bot API** — token in `.env` (`TELEGRAM_BOT_TOKEN`); runs via supervisor `telegram_bot` program
- **Nova Poshta API** — key `5cb1e3ebc23e75d737fd57c1e056ecc9`; sender FOP counterparty/contact/city/warehouse refs in `.env`
- **WayForPay** — merchant `y_store_in_ua`, secret/password in `.env`, webhook `/api/v2/payments/wayforpay/webhook`

## Deployment status — 2026-04-19 (session current)
- ✅ Repo `svetlanaslinko057/dedede2333` cloned and mirrored into `/app`
- ✅ Backend deps installed via `pip install -r requirements.txt`
- ✅ Frontend deps installed via `yarn install`
- ✅ `.env` filled with real keys from INTEGRATION.md (Telegram bot, Nova Poshta, WayForPay, JWT)
- ✅ `TMA_URL` / `APP_URL` / `WAYFORPAY_*URL` pointed to `https://bot-app-deploy.preview.emergentagent.com`
- ✅ Supervisor services RUNNING: `backend` (:8001), `frontend` (:3000), `mongodb`, `telegram_bot`
- ✅ `/api/health` → `{"status":"ok","service":"tma-api"}`
- ✅ `/api/tma/categories`, `/api/tma/home`, `/api/tma/store-info` — возвращают реальные данные (seed сработал)
- ✅ TMA UI рендерится по `/tma` с каруселями, хитами продаж, категориями, bottom-nav
- ✅ Telegram bot `@Ystore_app_bot` стартанул, polling активен, menu-button настроен на TMA URL

## URLs
- Preview: https://bot-app-deploy.preview.emergentagent.com
- TMA: https://bot-app-deploy.preview.emergentagent.com/tma
- Backend health: `/api/health`
- Bot: @Ystore_app_bot

## Next Tasks (awaiting user input)
- Доработка TMA — конкретные запросы от пользователя
- Опционально: проверить checkout flow с WayForPay в dev-режиме
- Опционально: проверить создание ТТН Нової Пошти (sandbox)
