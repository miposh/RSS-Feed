# Database Infrastructure

Новая инфраструктура базы данных, построенная по образцу `aiogram_bot_template`.

## Структура

```
app/infrastructure/database/
├── connection/          # Слой подключения к БД
│   ├── base.py         # Абстрактный базовый класс
│   ├── psycopg_connection.py  # Реализация для psycopg
│   └── connect_to_pg.py       # Функции подключения к PostgreSQL
├── models/             # Pydantic модели для валидации данных
│   ├── user.py
│   ├── channel.py
│   ├── rss_feed.py
│   ├── rss_post.py
│   └── feed_subscription.py
├── tables/             # Классы для работы с таблицами БД
│   ├── base.py        # Базовый класс таблицы
│   ├── enums/         # Enums для действий таблиц
│   ├── users.py
│   ├── channels.py
│   ├── rss_feeds.py
│   ├── rss_posts.py
│   └── feed_subscriptions.py
├── query/              # Обертки для результатов запросов
│   └── results.py     # SingleQueryResult, MultipleQueryResult
└── db.py              # Главный класс DB

```

## Использование

### 1. Подключение к БД

```python
from app.infrastructure.database import get_pg_connection, PsycopgConnection, DB

# Подключение к PostgreSQL
pg_conn = await get_pg_connection(
    db_name="mydb",
    host="localhost",
    port=5432,
    user="user",
    password="password",
)

# Обертка подключения
connection = PsycopgConnection(pg_conn)

# Инициализация DB
db = DB(connection)
```

### 2. Работа с пользователями

```python
# Добавить пользователя
user = await db.users.add(
    user_id=123456789,
    username="john_doe"
)

# Получить пользователя
user = await db.users.get_user(user_id=123456789)

# Обновить username
user = await db.users.update_username(
    user_id=123456789,
    username="new_username"
)

# Получить всех пользователей
users = await db.users.get_all_users()
```

### 3. Работа с каналами

```python
# Добавить канал
channel = await db.channels.add(
    channel_id=-1001234567890,
    username="my_channel",
    title="My Channel"
)

# Получить канал
channel = await db.channels.get_channel(channel_id=-1001234567890)

# Получить все каналы
channels = await db.channels.get_all_channels()
```

### 4. Работа с RSS лентами

```python
# Добавить RSS ленту
feed = await db.rss_feeds.add(
    url="https://example.com/feed.xml",
    title="Example Feed",
    owner_user_id=1,
)

# Получить ленту по URL
feed = await db.rss_feeds.get_feed_by_url(url="https://example.com/feed.xml")

# Обновить метаданные
feed = await db.rss_feeds.update_feed_metadata(
    feed_id=1,
    title="New Title",
    description="New Description"
)

# Обновить статус загрузки
feed = await db.rss_feeds.update_fetch_status(
    feed_id=1,
    last_status=200,
    etag="abc123"
)

# Получить ленты для загрузки
feeds = await db.rss_feeds.get_feeds_to_fetch()
```

### 5. Работа с постами

```python
# Добавить пост
post = await db.rss_posts.add(
    feed_id=1,
    guid="https://example.com/post/123",
    link="https://example.com/post/123",
    title="Example Post",
    summary="This is an example",
    published_at=datetime.now()
)

# Получить неотправленные посты
posts = await db.rss_posts.get_unsent_posts(limit=100)

# Отметить как отправленный
post = await db.rss_posts.mark_as_sent(post_id=1)

# Получить посты по ленте
posts = await db.rss_posts.get_posts_by_feed(feed_id=1, limit=50)
```

### 6. Работа с подписками

```python
# Создать подписку
subscription = await db.feed_subscriptions.add(
    feed_id=1,
    channel_id=1
)

# Получить подписки канала
subscriptions = await db.feed_subscriptions.get_subscriptions_by_channel(
    channel_id=1
)

# Получить каналы для ленты
channel_ids = await db.feed_subscriptions.get_channels_for_feed(feed_id=1)

# Удалить подписку
await db.feed_subscriptions.delete(feed_id=1, channel_id=1)
```

## Преимущества новой архитектуры

1. **Разделение ответственности**: Connection, Models, Tables, Query Results
2. **Типобезопасность**: Pydantic модели для валидации
3. **Логирование**: Автоматическое логирование всех операций
4. **Расширяемость**: Легко добавлять новые таблицы и методы
5. **Тестируемость**: Абстракция BaseConnection позволяет мокировать БД
6. **Чистый код**: Следование принципам SOLID

## Миграция со старой структуры

Старая структура `app/database` была удалена. Основные изменения:

- `app/database/database.py` → `app/infrastructure/database/db.py`
- `app/database/models/` (SQLAlchemy) → `app/infrastructure/database/models/` (Pydantic)
- `app/database/repositories/` → `app/infrastructure/database/tables/`
- Добавлен слой `connection` для абстракции БД
- Добавлен слой `query` для обработки результатов

## Примеры

См. `example_usage.py` в корне проекта для полного примера использования.
