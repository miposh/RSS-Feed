import requests
import feedparser
import ssl

def test_feed():
    # Configure SSL context for legacy servers
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        # Fetch the feed with requests
        response = requests.get('https://rozetked.me/rss.xml', timeout=30, verify=False)
        print(f'Status: {response.status_code}')
        print(f'Content type: {response.headers.get("content-type")}')
        
        content = response.text
        print(f'Content length: {len(content)}')
        
        # Parse the content with feedparser
        feed_data = feedparser.parse(content)
        
        print(f'Feed bozo: {feed_data.bozo}')
        print(f'Bozo exception: {feed_data.bozo_exception if feed_data.bozo else None}')
        print(f'Feed version: {feed_data.version}')
        print(f'Feed encoding: {feed_data.encoding}')
        print(f'Feed entries count: {len(feed_data.entries)}')
        
        if feed_data.entries:
            print(f'First entry title: {feed_data.entries[0].title}')
            print(f'First entry link: {feed_data.entries[0].link}')
            print(f'First entry guid: {getattr(feed_data.entries[0], "guid", "No guid")}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    test_feed() 