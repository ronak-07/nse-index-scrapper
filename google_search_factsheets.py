#!/usr/bin/env python3
"""
Google/DuckDuckGo Search for NSE Factsheet URLs

This script searches for factsheet PDFs for each index and extracts
the URL from search results, which can then be used by the download script.
"""

import re
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

try:
    from duckduckgo_search import DDGS
    USE_DUCKDUCKGO = True
except ImportError:
    USE_DUCKDUCKGO = False
    try:
        from googlesearch import search as google_search
        USE_GOOGLE = True
    except ImportError:
        USE_GOOGLE = False


def search_factsheet_url_ddg(index_name: str, max_results: int = 10) -> Optional[str]:
    """
    Search DuckDuckGo for factsheet PDF URL for the given index.
    
    Args:
        index_name: Name of the index (e.g., "Nifty 200 Momentum 30")
        max_results: Maximum number of search results to check
        
    Returns:
        PDF URL if found, None otherwise
    """
    # Construct search query
    query = f"{index_name} factsheet niftyindices.com pdf"
    
    try:
        print(f"  Searching DuckDuckGo: {query}...")
        
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query,
                max_results=max_results,
                region='in-en'  # India, English
            ))
        
        # Look for niftyindices.com PDF links
        for result in results:
            url = result.get('href', '')
            if 'niftyindices.com' in url.lower() and url.lower().endswith('.pdf'):
                print(f"  ✓ Found PDF: {url}")
                return url
            # Also check if it's a factsheet page
            if 'niftyindices.com' in url.lower() and 'factsheet' in url.lower():
                print(f"  ✓ Found factsheet page: {url}")
                return url
        
        print(f"  ✗ No niftyindices.com PDF found in top {max_results} results")
        return None
        
    except Exception as e:
        print(f"  ✗ Search error: {e}")
        return None


def search_factsheet_url_google_api(index_name: str, max_results: int = 10) -> Optional[str]:
    """
    Search using DuckDuckGo HTML (fallback method using requests).
    
    Args:
        index_name: Name of the index
        max_results: Maximum number of results to check (increased to 10)
        
    Returns:
        PDF URL if found, None otherwise
    """
    # Try multiple query variants
    queries = [
        f"{index_name} factsheet niftyindices.com pdf",
        f"{index_name} niftyindices factsheet",  # Without "pdf" keyword
        # Replace colons with spaces (e.g., "50:25:25" -> "50 25 25")
        f"{index_name.replace(':', ' ')} factsheet niftyindices.com pdf",
    ]
    
    for query_idx, query in enumerate(queries, 1):
        try:
            print(f"  Searching (HTML) [{query_idx}/{len(queries)}]: {query}...")
            
            # Use DuckDuckGo HTML search
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all result links (increased to check more results)
            results = soup.find_all('a', class_='result__a', href=True)[:max_results]
            
            for result in results:
                url = result.get('href', '')
                # DuckDuckGo uses redirect URLs, extract actual URL
                if 'uddg=' in url:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    if 'uddg' in params:
                        url = urllib.parse.unquote(params['uddg'][0])
                
                if 'niftyindices.com' in url.lower() and url.lower().endswith('.pdf'):
                    print(f"  ✓ Found PDF: {url}")
                    return url
                if 'niftyindices.com' in url.lower() and 'factsheet' in url.lower():
                    print(f"  ✓ Found factsheet page: {url}")
                    return url
            
            # Only print "not found" if this was the last query
            if query_idx == len(queries):
                print(f"  ✗ No niftyindices.com PDF found in top {max_results} results")
            else:
                print(f"  ✗ Not found in this query, trying next variant...")
            
            # Add a small delay between queries
            if query_idx < len(queries):
                time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ Search error: {e}")
            if query_idx < len(queries):
                continue
            return None
    
    return None


def search_factsheet_url_google(index_name: str, max_results: int = 10) -> Optional[str]:
    """
    Search Google for factsheet PDF URL for the given index.
    
    Args:
        index_name: Name of the index (e.g., "Nifty 200 Momentum 30")
        max_results: Maximum number of search results to check
        
    Returns:
        PDF URL if found, None otherwise
    """
    # Construct search query
    query = f"{index_name} factsheet nse niftyindices.com pdf"
    
    try:
        print(f"  Searching Google: {query}...")
        
        # Search Google (with delay to avoid rate limiting)
        results = google_search(
            query,
            num_results=max_results,
            lang='en',
            pause=2.0
        )
        
        # Look for niftyindices.com PDF links
        for url in results:
            if 'niftyindices.com' in url.lower() and url.lower().endswith('.pdf'):
                print(f"  ✓ Found PDF: {url}")
                return url
            if 'niftyindices.com' in url.lower() and 'factsheet' in url.lower():
                print(f"  ✓ Found factsheet page: {url}")
                return url
        
        print(f"  ✗ No niftyindices.com PDF found in top {max_results} results")
        return None
        
    except Exception as e:
        print(f"  ✗ Search error: {e}")
        return None


def search_factsheet_url(index_name: str, max_results: int = 10) -> Optional[str]:
    """
    Search for factsheet PDF URL for the given index.
    Uses DuckDuckGo if available, otherwise falls back to HTML search or Google.
    
    Args:
        index_name: Name of the index (e.g., "Nifty 200 Momentum 30")
        max_results: Maximum number of search results to check
        
    Returns:
        PDF URL if found, None otherwise
    """
    if USE_DUCKDUCKGO:
        return search_factsheet_url_ddg(index_name, max_results)
    elif USE_GOOGLE:
        return search_factsheet_url_google(index_name, max_results)
    else:
        # Fallback to HTML scraping
        return search_factsheet_url_google_api(index_name, max_results)


def process_indices_from_file(indices_file: Path, output_file: Path) -> Tuple[int, int]:
    """
    Process indices from file and search for their factsheet URLs.
    
    Args:
        indices_file: Path to indices.txt file
        output_file: Path to output file for URLs
        
    Returns:
        Tuple of (success_count, error_count)
    """
    # Read indices
    indices = []
    try:
        with open(indices_file, 'r', encoding='utf-8') as f:
            for line in f:
                index_name = line.strip()
                if index_name:
                    indices.append(index_name)
    except FileNotFoundError:
        print(f"Error: {indices_file} not found.")
        return 0, 0
    
    if not indices:
        print("No indices found in indices.txt")
        return 0, 0
    
    print(f"Found {len(indices)} indices to search.\n")
    
    success_count = 0
    error_count = 0
    found_urls = []
    not_found = []
    
    # Search for each index
    for idx, index_name in enumerate(indices, 1):
        print(f"[{idx}/{len(indices)}] {index_name}")
        
        url = search_factsheet_url(index_name)
        
        if url:
            found_urls.append(f"{index_name} : {url}")
            success_count += 1
        else:
            not_found.append(index_name)
            error_count += 1
        
        # Add delay between searches to avoid rate limiting
        if idx < len(indices):
            time.sleep(2)  # Increased delay
        print()
    
    # Write results to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in found_urls:
            f.write(f"{line}\n")
    
    # Print summary
    print(f"{'='*60}")
    print(f"Search complete!")
    print(f"  Found URLs: {success_count}")
    print(f"  Not found: {error_count}")
    print(f"  Results saved to: {output_file}")
    
    if not_found:
        print(f"\nIndices not found:")
        for index_name in not_found:
            print(f"  - {index_name}")
    
    return success_count, error_count


def main():
    """
    Main entry point for the script.
    """
    import sys
    
    BASE_DIR = Path(__file__).parent
    INDICES_FILE = BASE_DIR / "indices.txt"
    OUTPUT_FILE = BASE_DIR / "google_found_urls.txt"
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        INDICES_FILE = Path(sys.argv[1])
    
    if len(sys.argv) > 2:
        OUTPUT_FILE = Path(sys.argv[2])
    
    # Validate input file
    if not INDICES_FILE.exists():
        print(f"Error: {INDICES_FILE} does not exist.")
        sys.exit(1)
    
    # Process indices
    process_indices_from_file(INDICES_FILE, OUTPUT_FILE)


if __name__ == "__main__":
    main()
