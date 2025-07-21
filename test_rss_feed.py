#!/usr/bin/env python3
import sys
import requests
import feedparser
import urllib3
from urllib.parse import urlparse

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        # Check that scheme is either http or https
        if result.scheme not in ('http', 'https'):
            return False
        # Check that netloc is not empty
        return all([result.scheme, result.netloc])
    except Exception as e:
        print(f"URL validation error: {e}")
        return False

def test_feed(url: str) -> None:
    """Test an RSS feed URL."""
    print(f"Testing RSS feed: {url}")
    
    # Validate URL format
    if not is_valid_url(url):
        print("❌ Invalid URL format")
        return
    
    try:
        # Fetch the feed with requests, disabling chunked transfer encoding
        print("Fetching feed...")
        session = requests.Session()
        session.headers.update({
            'Accept-Encoding': 'identity',  # Disable compression
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'  # Добавляем пользовательский User-Agent
        })
        
        response = session.get(
            url, 
            timeout=30, 
            verify=False,
            stream=True  # Use streaming mode
        )
        
        print(f"Status: {response.status_code}")
        print(f"Content type: {response.headers.get('content-type')}")
        
        if response.status_code != 200:
            print(f"❌ HTTP error: {response.status_code}")
            return
        
        # Read content in chunks to avoid transfer encoding issues
        content = ""
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if chunk:
                # Ensure chunk is a string, convert from bytes if necessary
                if isinstance(chunk, bytes):
                    chunk = chunk.decode('utf-8', errors='replace')
                content += chunk
        
        print(f"Content length: {len(content)} characters")
        
        # Parse the content with feedparser
        print("Parsing feed...")
        feed_data = feedparser.parse(content)
        
        print(f"Feed bozo: {feed_data.bozo}")
        if feed_data.bozo and hasattr(feed_data, 'bozo_exception'):
            print(f"Bozo exception: {feed_data.bozo_exception}")
        
        print(f"Feed version: {feed_data.version}")
        print(f"Feed encoding: {feed_data.encoding}")
        
        if hasattr(feed_data, 'feed') and hasattr(feed_data.feed, 'title'):
            print(f"Feed title: {feed_data.feed.title}")
        
        if hasattr(feed_data, 'entries'):
            print(f"Feed entries count: {len(feed_data.entries)}")
            
            if feed_data.entries:
                print("\nFirst entry details:")
                entry = feed_data.entries[0]
                print(f"Title: {getattr(entry, 'title', 'No title')}")
                print(f"Link: {getattr(entry, 'link', 'No link')}")
                print(f"GUID: {getattr(entry, 'guid', getattr(entry, 'id', 'No guid'))}")
                print(f"Published: {getattr(entry, 'published', 'No publication date')}")
                
                print("\n✅ Feed successfully parsed!")
            else:
                print("❌ No entries found in the feed")
        else:
            print("❌ No entries attribute found in the feed")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_rss_feed.py <rss_feed_url>")
        sys.exit(1)
    
    test_feed(sys.argv[1]) 