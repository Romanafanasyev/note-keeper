# 📝 note-keeper

## 📌 Описание
`note-keeper` — это Telegram-бот и мини-система планирования, которая позволяет пользователю удобно управлять своими задачами на сегодня, завтра, неделю и месяц.
Он публикует напоминания в канал, присылает уведомления, хранит данные в SQLite, имеет простой API для работы с задачами и легко расширяется.
> Проект разработан с упором на **чистую архитектуру**, **тестируемость** и **надёжную структуру**, которая облегчает поддержку и расширение.

### Возможности
- ➕ Добавление, ✏️ редактирование и ❌ удаление задач из чата  
- 📋 Списки на **сегодня / неделю / месяц** одной командой  
- 🔔 Авто-напоминания **−24 ч** и **−90 мин**  
- 📢 Авто-посты в канале (сегодня, завтра, неделя, месяц)  
- 📄 Docker-образ, make-команды, GitHub Actions, unit-тесты  
- 🗄️ Данные и логи сохраняются во внешний volume (`/opt/planbot`)

---

## 🚀 Quick Start (Docker)

```bash
# 1. Клонируем проект
git clone https://github.com/<your-nick>/note-keeper.git
cd note-keeper

# 2. Создаём .env
cp .env.example .env          # впишите токен и id

# 3. Собираем и запускаем
make build        # docker build …
make run          # python -m bot.main  (для локальной отладки)

# продакшен-вариант на VPS
docker run -d \
  --name planbot \
  --restart unless-stopped \
  --env-file /opt/planbot/.env \
  -v /opt/planbot/data:/app/data \
  -v /opt/planbot/logs:/app/logs \
  romaamor66/planbot:0.8
```
---

## 🏗️ Архитектура проекта

```
bot/
├─ core/          – singleton-конфиг, инициализация БД
├─ handlers/      – тонкие Telegram-хендлеры (presentation layer)
├─ services/      – бизнес-логика (service-layer, DTO)
├─ repositories/  – доступ к данным (repository pattern)
├─ models/        – ORM-модели SQLAlchemy
├─ scheduler/     – APScheduler (cron + interval jobs)
├─ utils/         – логгер, валидаторы, парсеры
└─ main.py        – точка входа и DI-регистрация
```

Используемые паттерны


| Слой              | Паттерн           | Роль                               |
|-------------------|-------------------|------------------------------------|
| `core.config`     | Singleton         | Единый источник настроек           |
| `handlers/*`      | Command           | Каждая команда - отдельная функция |
| `services/*`      | Service Layer     | Инкапсулирует бизнес-правила       |
| `repositories/*`  | Repository        | Абстрагирует SQL                   |
| `utils/logger.py` | Factory           | Создает общий Rotating Logger      |
| `scheduler/*`     | Scheduler/Adapter | Тонкий адаптер над APScheduler     |

*Благодаря такому разделению код легко тестировать и расширять.*

---

## ⚙️ Переменные окружения


| Переменная | Описание                                  |
|------------|-------------------------------------------|
| BOT_TOKEN  | Токен Telegram-бота                       |
| CHANNEL_ID | ID канала/чата для постов                 |
| USER_ID    | ID пользователя для личных уведомлений    |
| TZ*        | Часовой пояс (по умолчанию `Europe/Moscow`) |

* `TZ` берётся из `.env`; если не указан — используется `Europe/Moscow`.

---

## 🛠️ Make-команды

| Команда       | Что делает                     |
|---------------|--------------------------------|
| `make dev`    | Запуск бота локально           |
| `make format` | `black + isort + flake8`       |
| `make test`   | PyTest с in-memory SQLite      |
| `make bump`   | `Авто-инкремент файла VERSION` |
| `make build`  | Запушить образ в Docker Hub    |
| `make deploy` | CI                             |

---

## 💬 Вклад

PR и issue — **welcome**.
Если нашли баг или есть идея улучшения — открывайте тикет или присылайте pull-request.



