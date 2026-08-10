"""Tests for RSS parsing — no network, no DB."""
from datetime import datetime, timezone

import pytest

from app.services.parser.rss_parser import RSSParser, parse_rss_feed


FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Test feed</title>
    <item>
      <guid>post-1</guid>
      <title>Первый пост</title>
      <link>https://example.com/1</link>
      <description>Краткое описание</description>
      <content:encoded>Полный текст статьи</content:encoded>
      <dc:creator>Иван Иванов</dc:creator>
      <pubDate>Tue, 10 Jun 2025 12:00:00 GMT</pubDate>
    </item>
    <item>
      <guid>post-2</guid>
      <title>Второй пост</title>
      <link>https://example.com/2</link>
    </item>
  </channel>
</rss>
"""


class TestFixMojibake:
    def test_repairs_latin1_mangled_cyrillic(self):
        broken = "Автомобили".encode("utf-8").decode("latin-1")
        assert RSSParser.fix_mojibake(broken) == "Автомобили"

    def test_leaves_clean_cyrillic_alone(self):
        assert RSSParser.fix_mojibake("Автомобили") == "Автомобили"

    def test_leaves_clean_ascii_alone(self):
        assert RSSParser.fix_mojibake("Hello world") == "Hello world"

    @pytest.mark.parametrize("text", ["", "ab"])
    def test_short_input_passes_through(self, text):
        assert RSSParser.fix_mojibake(text) == text

    def test_undecodable_text_is_returned_unchanged(self):
        # Contains a mojibake indicator ('Ð') but is not actually mangled UTF-8,
        # so the latin-1 -> utf-8 round trip must fail and return the input.
        text = "Ð Ð Ð not really mojibake"
        assert RSSParser.fix_mojibake(text) == text


class TestDecodeContent:
    def test_utf8_roundtrip(self):
        assert RSSParser.decode_content("Привет".encode("utf-8")) == "Привет"

    def test_falls_back_for_non_utf8_bytes(self):
        # 0xff is invalid UTF-8; latin-1 accepts any byte, so we must get a str back.
        assert isinstance(RSSParser.decode_content(b"\xff\xfe caf\xe9"), str)

    def test_empty_bytes(self):
        assert RSSParser.decode_content(b"") == ""


class TestParseFeed:
    def test_parses_valid_feed(self):
        feed = RSSParser.parse_feed(FEED)
        assert feed is not None
        assert len(feed.entries) == 2

    def test_rejects_malformed_xml(self):
        assert RSSParser.parse_feed("<rss><channel><item></oops></rss>") is None

    def test_plain_garbage_yields_no_entries(self):
        feed = RSSParser.parse_feed("this is not xml at all")
        assert feed is None or feed.entries == []


class TestExtractPosts:
    @pytest.fixture
    def posts(self):
        return RSSParser.extract_posts(RSSParser.parse_feed(FEED))

    def test_extracts_every_entry(self, posts):
        assert len(posts) == 2

    def test_maps_core_fields(self, posts):
        p = posts[0]
        assert p.guid == "post-1"
        assert p.title == "Первый пост"
        assert p.link == "https://example.com/1"
        assert "Краткое описание" in p.summary

    def test_prefers_content_encoded_for_full_text(self, posts):
        assert posts[0].content == "Полный текст статьи"

    def test_reads_dc_creator_as_author(self, posts):
        assert posts[0].author == "Иван Иванов"

    def test_published_time_is_timezone_aware(self, posts):
        assert posts[0].published_time is not None
        assert posts[0].published_time.tzinfo is not None

    def test_published_time_matches_pubdate(self, posts):
        expected = datetime(2025, 6, 10, 12, 0, tzinfo=timezone.utc)
        assert posts[0].published_time == expected

    def test_images_are_never_taken_from_rss(self, posts):
        assert all(p.image_urls == [] for p in posts)

    def test_entry_without_optional_fields_still_parses(self, posts):
        p = posts[1]
        assert p.guid == "post-2"
        assert p.author is None
        assert p.content == ""
        assert p.published_time is None

    def test_bad_entry_is_skipped_not_fatal(self):
        class Boom:
            def __getattr__(self, name):
                raise RuntimeError("exploding entry")

        feed = RSSParser.parse_feed(FEED)
        feed.entries.append(Boom())
        # The two good entries survive; the exploding one is dropped.
        assert len(RSSParser.extract_posts(feed)) == 2


class TestParseRSSFeedAsync:
    async def test_parses_bytes_end_to_end(self):
        posts = await parse_rss_feed(FEED.encode("utf-8"))
        assert posts is not None
        assert [p.guid for p in posts] == ["post-1", "post-2"]

    async def test_returns_none_on_malformed_feed(self):
        assert await parse_rss_feed(b"<rss><channel></oops></rss>") is None

    async def test_returns_empty_list_for_feed_without_entries(self):
        empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'
        assert await parse_rss_feed(empty) == []
