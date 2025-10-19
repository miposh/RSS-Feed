# Извлечение полного текста статей

## Обзор

Модуль `article_extractor.py` добавляет функциональность извлечения полного текста статей из веб-страниц, используя:
- **ScraperAPI** - для обхода защиты сайтов и получения HTML
- **newspaper4k** - для парсинга и извлечения чистого текста статьи

Теперь бот может отправлять полный текст статьи вместо сырых RSS-фидов.

## Установка зависимостей

```bash
pip install -r requirements.txt
```

Это установит необходимые пакеты:
- `scraperapi-sdk` - официальный SDK для ScraperAPI
- `newspaper4k` - библиотека для извлечения статей

## Настройка

### 1. Получение API ключа ScraperAPI

1. Зарегистрируйтесь на [ScraperAPI](https://www.scraperapi.com/)
2. Получите API ключ из [Dashboard](https://dashboard.scraperapi.com/)
3. Добавьте ключ в файл `.env`

### 2. Конфигурация .env файла

Скопируйте `.env.example` в `.env` и настройте:

```env
# ScraperAPI Configuration (Optional)
SCRAPER_ENABLED=true
SCRAPER_API_KEY=ваш_ключ_scraperapi
```

**Параметры:**
- `SCRAPER_ENABLED` - включить/выключить функцию (true/false)
- `SCRAPER_API_KEY` - ваш API ключ от ScraperAPI

## Как это работает

### Процесс извлечения статьи:

1. **RSS парсинг** - бот получает список новостей из RSS фида
2. **Проверка настроек** - если `SCRAPER_ENABLED=true`, активируется извлечение
3. **Загрузка HTML** - ScraperAPI загружает HTML страницы статьи
4. **Парсинг контента** - newspaper4k извлекает чистый текст статьи
5. **Отправка в чат** - полный текст статьи отправляется вместо RSS контента

### Последовательность:

```
RSS Feed → Ссылка на статью → ScraperAPI → HTML → newspaper4k → Чистый текст → Telegram
```

## Использование

### Автоматическое извлечение

После включения в `.env`, извлечение происходит автоматически для всех новых постов:

```python
# В new_rss_service.py
async def _process_post(self, post: RSSPost, ...):
    if self.scraper_enabled and post.link:
        full_article_text = await extract_article_content(post.link)
        if full_article_text:
            post.content = full_article_text
```

### Программное использование

Вы также можете использовать модуль напрямую:

```python
from parser.article_extractor import extract_article_content

# Извлечь текст статьи
article_text = await extract_article_content("https://example.com/article")
print(article_text)
```

## Особенности

### Работа без ScraperAPI

Если ScraperAPI отключен (`SCRAPER_ENABLED=false`), модуль всё равно работает:
- Использует встроенный загрузчик newspaper4k
- Может не работать на сайтах с защитой от ботов
- Подходит для простых сайтов без защиты

### Обработка ошибок

Модуль имеет встроенную обработку ошибок:
- Если извлечение не удалось, используется контент из RSS
- Все ошибки логируются
- Бот продолжает работу даже при сбоях

### Логирование

```python
logger.info("Успешно извлечен полный текст (5000 символов)")
logger.warning("Не удалось извлечь полный текст, используем RSS контент")
logger.error("Ошибка извлечения статьи: Connection timeout")
```

## Примеры

### Включить извлечение статей

```env
SCRAPER_ENABLED=true
SCRAPER_API_KEY=ваш_ключ
```

### Отключить извлечение (использовать только RSS)

```env
SCRAPER_ENABLED=false
```

### Комбинация с Gemini AI

Можно использовать оба функционала вместе:

```env
# Извлечь полный текст статьи
SCRAPER_ENABLED=true
SCRAPER_API_KEY=ваш_scraperapi_ключ

# Рерайтнуть через Gemini AI
GEMINI_ENABLED=true
GEMINI_API_KEY=ваш_gemini_ключ
```

**Последовательность:**
1. RSS → Ссылка
2. ScraperAPI → HTML
3. newspaper4k → Чистый текст
4. Gemini AI → Рерайт текста
5. Telegram → Отправка

## Ограничения

### ScraperAPI лимиты

- Бесплатный план: 1000 запросов/месяц
- Платные планы: от 10000 запросов/месяц
- См. [тарифы ScraperAPI](https://www.scraperapi.com/pricing/)

### Рекомендации

- Включайте ScraperAPI только для важных источников
- Используйте RSS контент для менее важных фидов
- Мониторьте использование API через [Dashboard](https://dashboard.scraperapi.com/)

## Поддержка языков

newspaper4k поддерживает автоматическое определение языка:
- Русский ✅
- Английский ✅
- И многие другие

```python
# Настройка языка (опционально)
article = Article(url, language='ru')
```

## Отладка

### Включить debug логи

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Проверить статус

```python
from parser.article_extractor import get_article_extractor

extractor = get_article_extractor()
print(f"ScraperAPI enabled: {extractor.scraper_enabled}")
print(f"API key configured: {bool(extractor.scraper_api_key)}")
```

## Устранение неполадок

### Проблема: "ScraperAPI включен, но API ключ не найден"

**Решение:** Проверьте файл `.env`:
```env
SCRAPER_API_KEY=ваш_ключ_здесь
```

### Проблема: "Не удалось извлечь текст статьи"

**Возможные причины:**
- Сайт блокирует доступ
- Неправильная структура HTML
- Статья за paywall

**Решение:** Бот автоматически использует RSS контент как fallback.

### Проблема: Превышен лимит ScraperAPI

**Решение:**
- Временно отключите: `SCRAPER_ENABLED=false`
- Обновите план на ScraperAPI
- Используйте только для важных источников

## Дополнительная информация

- [Документация ScraperAPI](https://docs.scraperapi.com/)
- [Документация newspaper4k](https://newspaper4k.readthedocs.io/)
- [ScraperAPI Python SDK](https://pypi.org/project/scraperapi-sdk/)

## Версии

- Python: 3.8+
- scraperapi-sdk: latest
- newspaper4k: latest
