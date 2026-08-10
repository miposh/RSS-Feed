# Деплой на Railway

Инструкция для этого проекта — Telegram-бот на long polling с PostgreSQL.

Ключевой момент: бот **не веб-сервис**. Он не слушает порт, ему не нужен домен и
healthcheck по HTTP. На Railway это обычный сервис без публичной сети.

---

## 1. Что понадобится

- Аккаунт на [railway.com](https://railway.com) и репозиторий проекта на GitHub.
- Токен бота от [@BotFather](https://t.me/BotFather).
- Опционально — [Railway CLI](https://docs.railway.com/guides/cli):
  ```bash
  npm i -g @railway/cli && railway login
  ```

---

## 2. Создать проект и базу

1. **New Project → Deploy PostgreSQL**. Railway поднимет базу и сам выдаст
   переменные `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`,
   `DATABASE_URL`.
2. Переименуйте сервис базы в `Postgres` (Settings → Service Name), если он
   называется иначе — имя используется в ссылках на переменные ниже.

База по умолчанию доступна только внутри проекта, через приватную сеть. Публичный
доступ (`DATABASE_PUBLIC_URL`) включать не нужно — он тарифицируется как egress.

---

## 3. Добавить сервис бота

**New → GitHub Repo → выберите репозиторий.**

Railway найдёт `Dockerfile` в корне и соберёт из него — Nixpacks/Railpack не
подключается, никакой настройки билдера не требуется. В логах сборки будет
`Using detected Dockerfile!`.

`docker/entrypoint.sh` уже делает всё необходимое при старте: генерирует
`.secrets.toml` из переменных окружения, ждёт базу и накатывает миграции.

---

## 4. Переменные окружения — главный шаг

`entrypoint.sh` читает имена `POSTGRES_*`, а Railway отдаёт `PG*`. Их нужно
связать вручную. В сервисе бота откройте **Variables → Raw Editor** и вставьте:

```env
BOT_TOKEN=<токен от BotFather>
ENV_FOR_DYNACONF=production

POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}

WAIT_FOR_DB=1
WAIT_FOR_DB_TIMEOUT=90
RUN_MIGRATIONS=1
AUTO_GENERATE_SECRETS_TOML=1

LOG_LEVEL_NAME=INFO
BOT_PARSE_MODE=HTML
RSS_CHECK_INTERVAL=300
CLEANUP_INTERVAL=86400
SENT_POSTS_RETENTION_DAYS=30
```

Синтаксис `${{Postgres.PGHOST}}` — это ссылка на переменную другого сервиса.
Railway подставляет значения при деплое, так что пароль нигде не дублируется.
Если сервис базы назван не `Postgres`, замените имя во всех пяти строках.

`APP_MEMORY_LIMIT`, `DB_MEMORY_LIMIT`, `APP_SHM_SIZE` из `.env.example` — это
параметры docker-compose. На Railway они не нужны, лимиты задаются планом.

---

## 5. Настройки сервиса

**Settings → Networking:** ничего не включайте. Домен боту не нужен — он сам
ходит в Telegram по long polling. Healthcheck оставьте пустым: HTTP-эндпоинта в
боте нет, и включённая проверка провалит деплой.

**Settings → Deploy → Restart Policy:** `ON_FAILURE`, 10 попыток.

Опционально это же можно зафиксировать в репозитории — создайте `railway.json`
в корне:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## 6. Память

В образ ставится Chromium — botasaurus запускает его для извлечения статей.
Это главный потребитель памяти.

- **Минимум 2 ГБ RAM** на сервис бота. На 512 МБ Chromium будет падать по OOM,
  и в логах вы увидите обрывающиеся воркеры без внятной ошибки.
- Если памяти не хватает, переключите канал на скрапер `scraperapi` (внешний
  API, Chromium не запускается) или вынесите браузер в отдельный сервис — см.
  раздел 8.

`CleanupService` сам перезапускает браузер по расписанию и чистит память, но
это смягчает рост, а не отменяет базовые требования.

---

## 7. Проверка

Деплой запускается автоматически после сохранения переменных. Смотрите
**Deployments → View Logs**, ожидаемая последовательность:

```
[entrypoint] Generating .secrets.toml from environment variables (if provided)
[entrypoint] Waiting for PostgreSQL ...
[entrypoint] PostgreSQL is reachable at ...
[entrypoint] Applying database migrations
✓ Migration process completed successfully!
Logging configured: level=INFO
Message queue started
Bot started successfully
Starting polling with allowed_updates: [...]
```

После этого напишите боту `/start` в Telegram.

Через CLI то же самое:
```bash
railway logs
```

---

## 8. Опционально: browser-service отдельным сервисом

Имеет смысл, если бот упирается в память: Chromium уезжает в свой контейнер.

1. **New → GitHub Repo**, тот же репозиторий, но в **Settings → Build** укажите
   **Root Directory** = `browser-service`.
2. В сервисе бота добавьте переменную:
   ```env
   BROWSER_SERVICE_URL=http://${{browser-service.RAILWAY_PRIVATE_DOMAIN}}:8000
   ```
   (подставьте фактическое имя сервиса).
3. В настройках каналов бота выберите тип скрапера `browser_service`.

**Важно про сеть.** Приватная сеть Railway в старых окружениях работает только
по IPv6, а `browser-service/Dockerfile` запускает uvicorn с `--host 0.0.0.0`
(только IPv4) — из бота сервис будет недоступен. Если столкнётесь с этим,
поменяйте команду запуска на `--host ::`. В окружениях, созданных после
16 октября 2025, DNS резолвится и в IPv4, и в IPv6, и менять ничего не нужно.
Публичный домен для browser-service включать не надо.

---

## 9. Если что-то не так

| Симптом | Причина |
|---|---|
| `ERROR: PostgreSQL is not reachable after 90s` | Не проставлены `POSTGRES_HOST`/`POSTGRES_PORT` или неверное имя сервиса в `${{...}}`. |
| Деплой падает на healthcheck | Указан `healthcheckPath`. Уберите — у бота нет HTTP. |
| `TelegramUnauthorizedError` | Неверный `BOT_TOKEN`. |
| Контейнер перезапускается без ошибок в логе | OOM. Поднимите память до 2 ГБ (см. раздел 6). |
| Миграции не накатились | `RUN_MIGRATIONS` не равен `1`. |
| Бот стартует, но каналы молчат | Парсинг не включён для канала, либо бот не админ в канале. |

Ручной прогон миграций, если нужно:
```bash
railway run python apply_migrations.py
```

---

## Замечание по безопасности

`.env` и `.secrets.toml` в `.gitignore` — пароли и токен в репозиторий не
попадают, всё в порядке.

Но `settings.toml` закоммичен, и в нём указан реальный IP, порт и пользователь
production-базы (`[default.postgres]`). Пароля там нет, так что это не утечка
доступа, но адрес базы светится в репозитории. На Railway эти значения не
используются — `entrypoint.sh` перезаписывает `.secrets.toml` из переменных
окружения, а они перекрывают `settings.toml`. Заменить хост на плейсхолдер
стоит отдельным коммитом.
