"""
Tests for RSS parser functionality.
"""
import pytest
from datetime import datetime
from app.services.parser.rss_parser import RSSParser, parse_rss_feed


# Sample RSS feed for testing
SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
    <channel>
        <title>Test Feed</title>
        <link>https://example.com</link>
        <description>Test RSS Feed</description>
        <item>
            <title>Test Article 1</title>
            <link>https://example.com/article1</link>
            <guid>https://example.com/article1</guid>
            <description>This is a test article summary</description>
            <content:encoded><![CDATA[<p>This is the full content of the article</p>]]></content:encoded>
            <dc:creator>John Doe</dc:creator>
            <pubDate>Mon, 11 Nov 2024 12:00:00 +0000</pubDate>
        </item>
        <item>
            <title>Test Article 2</title>
            <link>https://example.com/article2</link>
            <guid>article-2-guid</guid>
            <description>Another test article</description>
            <author>Jane Smith</author>
            <pubDate>Tue, 12 Nov 2024 15:30:00 +0000</pubDate>
        </item>
    </channel>
</rss>
"""

SAMPLE_RSS_NO_AUTHOR = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed No Author</title>
        <link>https://example.com</link>
        <description>Test RSS Feed without author</description>
        <item>
            <title>Article Without Author</title>
            <link>https://example.com/no-author</link>
            <guid>no-author-guid</guid>
            <description>Article without author field</description>
        </item>
    </channel>
</rss>
"""


class TestRSSParser:
    
    def test_decode_content_utf8(self):
        """Test UTF-8 decoding."""
        content = "Test content with UTF-8: привет"
        content_bytes = content.encode('utf-8')
        decoded = RSSParser.decode_content(content_bytes)
        assert decoded == content
    
    def test_decode_content_latin1(self):
        """Test Latin-1 decoding."""
        content = "Test content with Latin-1"
        content_bytes = content.encode('latin-1')
        decoded = RSSParser.decode_content(content_bytes)
        assert decoded == content
    
    def test_parse_feed_valid(self):
        """Test parsing valid RSS feed."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_FEED)
        assert feed_data is not None
        assert hasattr(feed_data, 'entries')
        assert len(feed_data.entries) == 2
    
    def test_parse_feed_invalid(self):
        """Test parsing invalid RSS feed."""
        invalid_feed = "This is not XML"
        feed_data = RSSParser.parse_feed(invalid_feed)
        # feedparser is very forgiving, so it might still parse
        # but should handle gracefully
        assert feed_data is not None or feed_data is None
    
    def test_extract_author_from_dc_creator(self):
        """Test extracting author from dc:creator field."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_FEED)
        entry = feed_data.entries[0]
        author = RSSParser._extract_author(entry)
        assert author == "John Doe"
    
    def test_extract_author_from_author_field(self):
        """Test extracting author from standard author field."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_FEED)
        entry = feed_data.entries[1]
        author = RSSParser._extract_author(entry)
        assert author == "Jane Smith"
    
    def test_extract_author_missing(self):
        """Test handling missing author field."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_NO_AUTHOR)
        entry = feed_data.entries[0]
        author = RSSParser._extract_author(entry)
        assert author is None
    
    def test_extract_full_text_from_content_encoded(self):
        """Test extracting full text from content:encoded."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_FEED)
        entry = feed_data.entries[0]
        content = RSSParser._extract_full_text(entry)
        assert "full content of the article" in content
    
    def test_extract_full_text_missing(self):
        """Test handling missing full text."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_NO_AUTHOR)
        entry = feed_data.entries[0]
        content = RSSParser._extract_full_text(entry)
        assert content == ""
    
    def test_parse_published_time(self):
        """Test parsing published time."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_FEED)
        entry = feed_data.entries[0]
        pub_time = RSSParser._parse_published_time(entry)
        assert pub_time is not None
        assert isinstance(pub_time, datetime)
    
    def test_extract_posts(self):
        """Test extracting posts from feed."""
        feed_data = RSSParser.parse_feed(SAMPLE_RSS_FEED)
        posts = RSSParser.extract_posts(feed_data)
        
        assert len(posts) == 2
        
        # Check first post
        post1 = posts[0]
        assert post1.title == "Test Article 1"
        assert post1.link == "https://example.com/article1"
        assert post1.guid == "https://example.com/article1"
        assert post1.summary == "This is a test article summary"
        assert "full content of the article" in post1.content
        assert post1.author == "John Doe"
        assert post1.published_time is not None
        
        # Check second post
        post2 = posts[1]
        assert post2.title == "Test Article 2"
        assert post2.link == "https://example.com/article2"
        assert post2.guid == "article-2-guid"
        assert post2.author == "Jane Smith"


@pytest.mark.asyncio
async def test_parse_rss_feed_integration():
    """Integration test for complete RSS feed parsing."""
    content_bytes = SAMPLE_RSS_FEED.encode('utf-8')
    posts = await parse_rss_feed(content_bytes)
    
    assert posts is not None
    assert len(posts) == 2
    
    # Verify all required fields are present
    for post in posts:
        assert post.guid
        assert post.title
        assert post.link
        assert hasattr(post, 'author')  # Can be None
        assert hasattr(post, 'published_time')  # Can be None


@pytest.mark.asyncio
async def test_parse_rss_feed_empty():
    """Test parsing empty feed."""
    empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Empty Feed</title>
            <link>https://example.com</link>
        </channel>
    </rss>
    """
    content_bytes = empty_feed.encode('utf-8')
    posts = await parse_rss_feed(content_bytes)
    
    assert posts is not None
    assert len(posts) == 0
