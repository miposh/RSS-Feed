# Docker / VPS / Dokploy

## Что добавлено

- `Dockerfile` с Python + Chromium (для Botasaurus)
- `docker/entrypoint.sh`:
  - генерирует `.secrets.toml` из env-переменных
  - ждёт PostgreSQL
  - запускает миграции
  - стартует бота
- `docker-compose.yml` с `app` + `db`
- ограничения памяти для VPS

## Быстрый запуск локально / на VPS (Docker Compose)

1. Создайте `.env`:

```bash
cp .env.example .env
```

2. Обязательно заполните:

- `BOT_TOKEN`
- `POSTGRES_PASSWORD`

3. Запустите:

```bash
docker compose up -d --build
```

4. Логи:

```bash
docker compose logs -f app
```

## Ограничение памяти

Лимиты уже прописаны в `docker-compose.yml`:

- `app`: `APP_MEMORY_LIMIT` (по умолчанию `1g`)
- `db`: `DB_MEMORY_LIMIT` (по умолчанию `512m`)

Меняются через `.env`, например:

```env
APP_MEMORY_LIMIT=1536m
DB_MEMORY_LIMIT=768m
APP_SHM_SIZE=512m
```

`APP_SHM_SIZE` важен для Chromium/Botasaurus (иначе возможны падения вкладок).

## Рекомендации для VPS (Botasaurus/Chromium)

- Минимум: `2 vCPU`, `4 GB RAM`
- Лучше: `4 vCPU`, `6-8 GB RAM` при большем количестве RSS/источников
- Диск: от `20 GB` (PostgreSQL + логи + Docker layers)

## Развёртывание через Dokploy (Compose)

### 1. Подготовить VPS

- Установите Docker/док-пакеты, если Dokploy не ставит их автоматически
- Установите Dokploy на VPS (по официальной инструкции)

### 2. Залить проект в Git (GitHub/GitLab)

Dokploy удобнее подключать к репозиторию, а не загружать архивом.

### 3. Создать приложение в Dokploy

- `Project` -> `Create Application`
- Тип: `Docker Compose`
- Подключите репозиторий
- В качестве compose-файла укажите: `docker-compose.yml`

### 4. Добавить переменные окружения в Dokploy

Минимально обязательные:

- `BOT_TOKEN`
- `POSTGRES_PASSWORD`

Рекомендуемые:

- `ENV_FOR_DYNACONF=production`
- `POSTGRES_DB=rss_bot`
- `POSTGRES_USER=postgres`
- `POSTGRES_HOST=db`
- `POSTGRES_PORT=5432`
- `APP_MEMORY_LIMIT=1g`
- `DB_MEMORY_LIMIT=512m`
- `APP_SHM_SIZE=256m`

### 5. Хранилище данных

В compose уже есть named volume:

- `pg_data` для PostgreSQL

Это достаточно для базового развёртывания. Если хотите внешний PostgreSQL, удалите/отключите сервис `db` и задайте `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` от внешней БД.

### 6. Deploy

- Нажмите `Deploy`
- Проверьте логи `db`, затем `app`
- После первого старта бот автоматически выполнит миграции (если `RUN_MIGRATIONS=1`)

## Полезные команды (Compose)

Пересборка:

```bash
docker compose up -d --build
```

Перезапуск только приложения:

```bash
docker compose restart app
```

Остановка:

```bash
docker compose down
```

Остановка без удаления БД-данных:

- `pg_data` сохраняется автоматически (named volume)
