#!/usr/bin/env python3
"""
Test script for multi-URL scraping with progress tracking
"""

import sys
sys.path.insert(0, '/Users/pc/dev/techbubble/ai-bot/app-1')

from processor import scrape_url, extract_same_domain_links
from bs4 import BeautifulSoup

def test_progress_tracking():
    """Test progress tracking with a real URL"""
    
    print("=" * 60)
    print("Testing Multi-URL Scraping with Progress Tracking")
    print("=" * 60)
    
    # Example URL (using a simple website that works)
    test_url = "https://example.com"
    
    print(f"\n📍 Starting to scrape: {test_url}")
    print("-" * 60)
    
    # Progress tracker
    progress_log = []
    
    def log_progress(event_type, data):
        """Log progress events"""
        progress_log.append((event_type, data))
        
        if event_type == 'scraping_start':
            print(f"✓ Started scraping: {data['url']}")
        
        elif event_type == 'links_discovered':
            print(f"\n🔗 Links Discovered: {data['count']}")
            if data['links']:
                for i, link in enumerate(data['links'], 1):
                    print(f"   {i}. {link}")
        
        elif event_type == 'scraping_progress':
            percent = (data['current'] / data['total']) * 100
            status_icon = {
                'scraping': '⏳',
                'success': '✓',
                'failed': '✗'
            }.get(data['status'], '?')
            print(f"{status_icon} [{percent:3.0f}%] {data['current']}/{data['total']}: {data['url']}")
            if 'error' in data and data['error']:
                print(f"   Error: {data['error']}")
        
        elif event_type == 'scraping_complete':
            print(f"\n✓ Completed! Scraped {data['total_urls']} pages")
        
        elif event_type == 'scraping_error':
            print(f"\n✗ Error: {data['error']}")
    
    try:
        # Run scraping with progress tracking
        result = scrape_url(test_url, progress_callback=log_progress)
        
        print("\n" + "=" * 60)
        print("RESULT SUMMARY")
        print("=" * 60)
        
        if result['success']:
            print(f"✓ Success!")
            print(f"  Main Title: {result['title']}")
            print(f"  URLs Scraped: {result['urls_scraped']}")
            print(f"  Content Length: {len(result['content'])} characters")
            print(f"  Related URLs: {len(result['related_urls'])}")
            
            print(f"\n📋 Content Preview (first 200 chars):")
            print(f"  {result['content'][:200]}...")
            
            print(f"\n📊 Progress Events Logged: {len(progress_log)}")
            for i, (event_type, data) in enumerate(progress_log, 1):
                print(f"  {i}. {event_type}: {list(data.keys())}")
        else:
            print(f"✗ Failed: {result.get('error')}")
    
    except Exception as e:
        print(f"\n✗ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

def test_link_extraction():
    """Test link extraction logic"""
    print("\n\nTesting Link Extraction")
    print("=" * 60)
    
    # Sample HTML
    html = """
    <html>
        <body>
            <a href="/">Home</a>
            <a href="/about">About</a>
            <a href="/contact">Contact</a>
            <a href="https://external.com">External</a>
            <a href="#section">Fragment</a>
            <a href="javascript:void(0)">JavaScript</a>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, 'html.parser')
    base_url = "https://example.com/page"
    
    links = extract_same_domain_links(soup, base_url, max_links=10)
    
    print(f"Base URL: {base_url}")
    print(f"Found {len(links)} same-domain links:")
    for link in links:
        print(f"  • {link}")
    
    print("=" * 60)

if __name__ == "__main__":
    print("\n🧪 Running Multi-URL Scraping Tests\n")
    
    try:
        test_progress_tracking()
        test_link_extraction()
    except Exception as e:
        print(f"Test suite error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✓ Tests completed!")
