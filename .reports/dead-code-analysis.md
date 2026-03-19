# Dead Code Analysis Report

**Generated:** 2026-02-20
**Project:** RSS Feed Bot

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Unused Files | 1 | SAFE |
| Unused Functions/Methods | 18 | CAUTION |
| Unused Dependencies | 1 | SAFE |
| Unused Config | 1 | CAUTION |

---

## 1. UNUSED FILES

### SAFE: Can be safely deleted

#### `app/services/utils/validators.py`
- **Status:** NOT IMPORTED anywhere in the codebase
- **Contains:** `is_valid_url()`, `validate_rss_feed()` functions
- **Issue:** Has broken imports: `from fetcher.http_client` and `from parser.rss_parser` (missing `app.services.` prefix)
- **Recommendation:** DELETE - File is broken and unused

---

## 2. UNUSED FUNCTIONS/METHODS

### Database Tables - CAUTION

These methods exist in database table classes but are never called from application code:

#### `app/infrastructure/database/tables/users.py`
| Method | Line | Usage |
|--------|------|-------|
| `get_user_by_username()` | 64 | NOT USED |
| `get_all_users()` | 91 | NOT USED |
| `update_username()` | 77 | NOT USED |
| `delete()` | 42 | NOT USED |

#### `app/infrastructure/database/tables/channels.py`
| Method | Line | Usage |
|--------|------|-------|
| `get_channel_by_id()` | 71 | NOT USED |
| `update_channel()` | 86 | NOT USED |
| `enable_parsing()` | 138 | NOT USED (toggle_parsing is used instead) |
| `disable_parsing()` | 153 | NOT USED (toggle_parsing is used instead) |

#### `app/infrastructure/database/tables/rss_feeds.py`
| Method | Line | Usage |
|--------|------|-------|
| `update_feed_metadata()` | 89 | NOT USED |
| `set_backoff()` | 172 | NOT USED |
| `enable_feed()` | 187 | NOT USED |
| `disable_feed()` | 202 | NOT USED |
| `get_feeds_to_fetch()` | 217 | NOT USED |
| `get_all_feeds()` | 233 | NOT USED |

#### `app/infrastructure/database/tables/rss_posts.py`
| Method | Line | Usage |
|--------|------|-------|
| `get_post()` | 56 | NOT USED |
| `get_unsent_posts()` | 100 | NOT USED |
| `get_posts_by_feed()` | 128 | NOT USED |

#### `app/infrastructure/database/tables/feed_subscriptions.py`
| Method | Line | Usage |
|--------|------|-------|
| `get_subscription()` | 49 | NOT USED |
| `get_subscriptions_by_feed()` | 62 | NOT USED |
| `get_channels_for_feed()` | 90 | NOT USED |

### Services - CAUTION

#### `app/services/chat_service.py`
| Method | Line | Usage |
|--------|------|-------|
| `register_chat()` | 20 | NOT USED |
| `remove_feed_from_chat()` | 73 | NOT USED (remove_feed_by_id is used instead) |

#### `app/services/scrapers/factory.py`
| Method | Line | Usage |
|--------|------|-------|
| `ScraperFactory.get_available_types()` | 47 | NOT USED |

#### `app/services/parser/article_extractor.py`
| Function | Line | Usage |
|----------|------|-------|
| `get_article_extractor()` | 139 | NOT USED (global singleton pattern not used) |

#### `app/services/fetcher/http_client.py`
| Function | Line | Usage |
|----------|------|-------|
| `close_http_client()` | 232 | NOT USED |

---

## 3. UNUSED DEPENDENCIES

### `requirements.txt` Analysis

| Dependency | Status | Notes |
|------------|--------|-------|
| aiogram | USED | Core bot framework |
| aiogram-dialog | USED | Dialog management |
| alembic | USED | Database migrations |
| dynaconf | USED | Config loading |
| feedparser | USED | RSS parsing |
| httpx | USED | HTTP client |
| scraperapi-sdk | USED | ScraperAPI integration |
| botasaurus | USED | Web scraping |
| newspaper4k | USED | Article extraction |
| Brotli | USED | Compression support |
| lxml-html-clean | USED | HTML cleaning |
| psycopg | USED | PostgreSQL driver |
| pydantic | USED | Data validation |
| asyncpg | NOT USED | psycopg_pool is used instead |
| psycopg_pool | USED | Connection pooling |
| pytest | USED | Testing |
| pytest-asyncio | USED | Async testing |

### Unused Config

#### `config/config.py`
| Config | Line | Usage |
|--------|------|-------|
| `RedisConfig` | 31 | DEFINED but Redis is NOT USED anywhere in codebase |

---

## 4. COMMENTED-OUT CODE

### `app/bot/bot.py` (Lines 46-62)
- Contains commented-out `set_bot_commands()` function
- **Recommendation:** DELETE if not planned for future use

---

## 5. PROPOSED DELETIONS

### SAFE TO DELETE (Test not required)

1. **`app/services/utils/validators.py`** - Broken file, not imported anywhere
2. **`asyncpg`** from `requirements.txt` - Unused dependency
3. Commented code in `app/bot/bot.py` (lines 46-62)

### CAUTION - Review Before Deletion

These are "orphan" methods that might be:
- Reserved for future use
- Part of a standard repository pattern
- Used by tests (not analyzed)

**Unused Database Methods:**
- Consider keeping as part of repository pattern for future extensibility
- If cleanup desired, remove in batches and run tests

**Unused Service Methods:**
- `ChatService.register_chat()` - May be intended for future use
- `ChatService.remove_feed_from_chat()` - Wrapper method, remove if `remove_feed_by_id` is sufficient
- `close_http_client()` - Should be called on shutdown, consider adding to `on_shutdown()`
- `RedisConfig` - Remove if Redis integration is not planned

---

## 6. ACTION ITEMS

### Immediate (SAFE)

- [ ] Delete `app/services/utils/validators.py`
- [ ] Remove `asyncpg` from `requirements.txt`
- [ ] Remove commented code in `app/bot/bot.py`

### Review Required (CAUTION)

- [ ] Decide on keeping/removing unused database methods
- [ ] Remove `RedisConfig` if Redis not planned
- [ ] Add `close_http_client()` call to shutdown sequence or remove it

---

## 7. NOTES

- No tests were found in the codebase to verify changes against
- The unused database methods follow a common repository pattern and may be intentional
- The `validators.py` file has broken imports and would not work even if called
