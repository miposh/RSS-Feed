"""
RSS feed parser with encoding detection and error handling.
"""
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

import feedparser
from app.services.parser.models import RSSPost

logger = logging.getLogger(__name__)


class RSSParser:
    @staticmethod
    def fix_mojibake(text: str) -> str:
        """
        Исправляет проблемы с кодировкой (mojibake).
        Когда UTF-8 текст был неправильно декодирован как Latin-1/Windows-1252.
        
        Примеры:
        - "ГЂГўГІГ®Г¬Г®ГЎГЁГ«ГЁ" -> "Автомобили" (Windows-1251)
        - "Ð²ÑÐ¾Ð¼Ð¾Ð±Ð¸Ð»Ð¸" -> "Автомобили" (Latin-1)
        """
        if not text or len(text) < 3:
            return text
        
        # Проверяем наличие характерных символов mojibake
        # Для кириллицы в UTF-8, декодированной как Latin-1: Ð, Ñ, Ð¾, Ð¸, Ð°, и т.д.
        # Для кириллицы в UTF-8, декодированной как Windows-1252: Г, Гў, ГЁ, и т.д.
        mojibake_patterns = [
            # Latin-1 mojibake (наиболее частый случай)
            ('Ð', 'Ñ', 'Ð¾', 'Ð¸', 'Ð°', 'Ñ', 'Ð²', 'Ð»'),
            # Windows-1252 mojibake
            ('Г', 'Гў', 'ГЁ', 'Г®', 'Г ', 'Г±', 'ГІ', 'Гј', 'Гђ'),
        ]
        
        has_mojibake = any(
            any(indicator in text for indicator in pattern)
            for pattern in mojibake_patterns
        )
        
        if not has_mojibake:
            return text
        
        try:
            # Пытаемся перекодировать: str -> latin-1 bytes -> utf-8 str
            text_bytes = text.encode('latin-1')
            fixed_text = text_bytes.decode('utf-8')
            
            # Проверяем, что результат выглядит разумно
            # Должно быть достаточно кириллических символов
            cyrillic_chars = sum(1 for c in fixed_text if '\u0400' <= c <= '\u04FF')
            if cyrillic_chars > 0:
                logger.info(f"Fixed mojibake in text (first 50 chars): '{text[:50]}...' -> '{fixed_text[:50]}...'")
                return fixed_text
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            logger.debug(f"Failed to fix mojibake for '{text[:50]}...': {e}")
        
        return text
    
    @staticmethod
    def decode_content(content_bytes: bytes) -> str:
        try:
            return content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
        
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                return content_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        logger.warning(
            "Failed to decode with known encodings, using replacement",
            extra={"size_bytes": len(content_bytes)}
        )
        return content_bytes.decode('utf-8', errors='replace')
    
    @staticmethod
    def parse_feed(content: str) -> Optional[feedparser.FeedParserDict]:
        try:
            feed_data = feedparser.parse(content)
            
            if feed_data.bozo and feed_data.bozo_exception:
                error_str = str(feed_data.bozo_exception).lower()
                critical_errors = ['not well-formed', 'syntax error', 'mismatched tag']
                
                if any(err in error_str for err in critical_errors):
                    logger.error(
                        "Critical feed parsing error",
                        extra={"error": str(feed_data.bozo_exception)}
                    )
                    return None
                else:
                    logger.warning(
                        "Minor feed parsing issue",
                        extra={"error": str(feed_data.bozo_exception)}
                    )
            
            if not hasattr(feed_data, 'entries'):
                logger.error("Feed has no entries attribute")
                return None
            
            return feed_data
        
        except Exception as e:
            logger.error(
                f"Unexpected parsing error: {e}",
                exc_info=True
            )
            return None
    
    @staticmethod
    def extract_posts(feed_data: feedparser.FeedParserDict) -> List[RSSPost]:
        posts = []
        
        for entry in feed_data.entries:
            try:
                post = RSSParser._parse_entry(entry)
                posts.append(post)
            except Exception as e:
                # getattr can itself raise here, which would defeat the skip.
                try:
                    entry_title = getattr(entry, 'title', 'Unknown')
                except Exception:
                    entry_title = 'Unknown'
                logger.warning(
                    f"Failed to parse entry: {e}",
                    extra={"entry_title": entry_title},
                    exc_info=True
                )
                continue
        
        return posts
    
    @staticmethod
    def _parse_entry(entry) -> RSSPost:
        entry_id = getattr(entry, 'guid', getattr(entry, 'id', entry.link))
        
        title = getattr(entry, 'title', 'No title')
        link = getattr(entry, 'link', '')
        summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
        
        # Извлекаем полный текст из различных возможных тегов
        content = RSSParser._extract_full_text(entry)
        
        # Извлекаем автора
        author = RSSParser._extract_author(entry)

        # Исправляем проблемы с кодировкой во всех текстовых полях
        title = RSSParser.fix_mojibake(title)
        summary = RSSParser.fix_mojibake(summary)
        content = RSSParser.fix_mojibake(content)
        if author:
            author = RSSParser.fix_mojibake(author)

        # Не извлекаем изображения из RSS - только через scraper
        image_urls = []

        published_time = RSSParser._parse_published_time(entry)
        
        return RSSPost(
            guid=entry_id,
            title=title,
            link=link,
            summary=summary,
            content=content,
            author=author,
            image_urls=image_urls,
            published_time=published_time
        )
    
    @staticmethod
    def _extract_author(entry) -> Optional[str]:
        """
        Извлекает автора статьи из различных возможных тегов.
        Проверяет: author, dc:creator, author_detail
        """
        # Проверяем стандартный author
        if hasattr(entry, 'author') and entry.author:
            return entry.author
        
        # Проверяем dc:creator (Dublin Core)
        if hasattr(entry, 'dc_creator') and entry.dc_creator:
            return entry.dc_creator
        
        # Проверяем author_detail
        if hasattr(entry, 'author_detail') and entry.author_detail:
            if isinstance(entry.author_detail, dict):
                return entry.author_detail.get('name', '')
        
        return None
    
    @staticmethod
    def _extract_full_text(entry) -> str:
        """
        Извлекает полный текст статьи из различных возможных тегов.
        Проверяет в порядке приоритета:
        1. yandex:full-text (используется 360.ru и другими)
        2. content:encoded (распространенный в RSS)
        3. content (стандартный Atom)
        4. Возвращает пустую строку, если ничего не найдено
        """
        # 1. Проверяем yandex:full-text (feedparser заменяет : на _)
        if hasattr(entry, 'yandex_full-text'):
            text = getattr(entry, 'yandex_full-text', '')
            if text:
                logger.debug("Extracted full text from yandex:full-text")
                return text
        
        # Альтернативный вариант написания
        if hasattr(entry, 'yandex_fulltext'):
            text = getattr(entry, 'yandex_fulltext', '')
            if text:
                logger.debug("Extracted full text from yandex:fulltext")
                return text
        
        # 2. Проверяем content:encoded
        if hasattr(entry, 'content_encoded'):
            text = getattr(entry, 'content_encoded', '')
            if text:
                logger.debug("Extracted full text from content:encoded")
                return text
        
        # 3. Проверяем стандартный content (обычно массив)
        if hasattr(entry, 'content') and entry.content:
            try:
                text = entry.content[0].get('value', '')
                if text:
                    logger.debug("Extracted full text from content")
                    return text
            except (IndexError, AttributeError, TypeError, KeyError):
                pass
        
        # 4. Возвращаем пустую строку, если полный текст не найден
        return ''
    
    @staticmethod
    def _parse_published_time(entry) -> Optional[datetime]:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                return dt.astimezone(timezone(timedelta(hours=3)))
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse published_parsed: {e}")
        
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                return dt.astimezone(timezone(timedelta(hours=3)))
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse updated_parsed: {e}")
        
        return None


async def parse_rss_feed(content_bytes: bytes) -> Optional[List[RSSPost]]:
    """
    Parse RSS feed asynchronously.
    
    Runs CPU-bound feedparser.parse() in a thread pool executor
    to avoid blocking the event loop.
    """
    content = RSSParser.decode_content(content_bytes)
    
    # Run synchronous feedparser.parse() in executor to avoid blocking
    loop = asyncio.get_running_loop()
    feed_data = await loop.run_in_executor(None, RSSParser.parse_feed, content)
    
    if not feed_data:
        return None
    
    if not feed_data.entries:
        logger.warning("Feed has no entries")
        return []
    
    # Extract posts also in executor (can be CPU-intensive for large feeds)
    posts = await loop.run_in_executor(None, RSSParser.extract_posts, feed_data)
    
    logger.info(
        "Feed parsed successfully",
        extra={
            "entries_count": len(feed_data.entries),
            "posts_extracted": len(posts)
        }
    )
    
    return posts
