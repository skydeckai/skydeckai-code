import os
import random
import time
from typing import List
from urllib.parse import urlparse

import requests
from mcp.types import TextContent

from .state import state


def web_fetch_tool():
    return {
        "name": "web_fetch",
        "description": "Fetch URL content with HTML→markdown conversion. 10MB limit. "
                    "USE: Get web data, API responses, documentation. "
                    "NOT: Complex auth, session management, OAuth interactions. "
                    "TIP: Use web_search first to find URLs. "
                    "Auto-converts HTML to markdown",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch (http/https only). Examples: 'https://example.com', 'https://api.github.com/repos/user/repo'."
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers. Examples: {'User-Agent': 'SkyDeckAI', 'Accept': 'application/json'}.",
                    "default": {}
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds. Default: 10.",
                    "default": 10
                },
                "save_to_file": {
                    "type": "string",
                    "description": "Optional save path. Examples: 'downloads/page.html', 'data/api_response.json'.",
                    "default": None
                },
                "convert_html_to_markdown": {
                    "type": "boolean",
                    "description": "Convert HTML content to markdown for better readability. Default: true.",
                    "default": True
                }
            },
            "required": ["url"]
        }
    }


async def handle_web_fetch(arguments: dict) -> List[TextContent]:
    """Handle fetching content from a URL."""
    url = arguments.get("url")
    headers = arguments.get("headers", {})
    timeout = arguments.get("timeout", 10)
    save_to_file = arguments.get("save_to_file")
    convert_html_to_markdown = arguments.get("convert_html_to_markdown", True)

    if not url:
        raise ValueError("URL must be provided")

    # Basic URL validation
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {url}. Must include scheme (http/https) and domain.")

    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}. Only http and https are supported.")

    # Add a default User-Agent if not provided
    if "User-Agent" not in headers:
        headers["User-Agent"] = "SkyDeckAI-Web-Fetch/1.0"

    # Validate and prepare file path if saving to file
    full_save_path = None
    if save_to_file:
        if os.path.isabs(save_to_file):
            full_save_path = os.path.abspath(save_to_file)
        else:
            full_save_path = os.path.abspath(os.path.join(state.allowed_directory, save_to_file))

        # Security check
        if not full_save_path.startswith(state.allowed_directory):
            raise ValueError(f"Access denied: Path ({full_save_path}) must be within allowed directory")

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_save_path), exist_ok=True)

    try:
        # Make the request with a maximum size limit to prevent abuse
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True  # Use streaming for better control over large responses
        )

        # Check if response is successful
        response.raise_for_status()

        # Get content type from headers
        content_type = response.headers.get("Content-Type", "").lower()

        # Maximum size limit (10MB)
        max_size = 10 * 1024 * 1024
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size:
                raise ValueError(f"Response too large. Maximum size is {max_size // (1024 * 1024)}MB.")

        # Save to file if requested
        if full_save_path:
            with open(full_save_path, 'wb') as f:
                f.write(content)

        # Try to decode the content
        try:
            text_content = content.decode('utf-8')

            # Convert HTML to markdown if requested and content appears to be HTML
            if convert_html_to_markdown and ("html" in content_type or text_content.strip().startswith(("<!DOCTYPE", "<html"))):
                try:
                    # Using the html2text library to convert HTML to markdown
                    # Need to import here to avoid dependency issues if the library is not installed
                    import html2text
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.ignore_emphasis = False
                    h.body_width = 0  # Don't wrap text
                    text_content = h.handle(text_content)
                except ImportError:
                    # Add note that html2text needs to be installed
                    text_content = f"NOTE: Could not convert HTML to markdown because html2text library is not installed.\n\n{text_content}"

        except UnicodeDecodeError:
            # If content can't be decoded as utf-8, provide info about binary content
            if full_save_path:
                return [TextContent(
                    type="text",
                    text=f"Binary content saved to {save_to_file} (size: {len(content)} bytes, type: {content_type})"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Binary content received (size: {len(content)} bytes, type: {content_type})"
                )]

        # Success message
        status_info = f"HTTP {response.status_code}"
        size_info = f"{len(content)} bytes"
        save_info = f", saved to {save_to_file}" if full_save_path else ""
        format_info = " (converted to markdown)" if convert_html_to_markdown and ("html" in content_type or text_content.strip().startswith(("<!DOCTYPE", "<html"))) else ""

        result = [TextContent(
            type="text",
            text=f"{status_info}, {size_info}{save_info}{format_info}:\n\n{text_content}"
        )]

        return result

    except requests.exceptions.RequestException as e:
        # Handle request-related errors
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message = f"HTTP {e.response.status_code}: {error_message}"

        raise ValueError(f"Error fetching URL ({url}): {error_message}")
    except Exception as e:
        # Handle other errors
        raise ValueError(f"Error processing content from {url}: {str(e)}")


def web_search_tool():
    return {
        "name": "web_search",
        "description": "Web search with Bing/DuckDuckGo. Returns titles, URLs, snippets. "
                    "USE: Find current information, research topics. "
                    "NOT: Private data, authenticated content, interactive sites. "
                    "TIP: Use with web_fetch for detailed content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (be specific). Examples: 'latest python release features', 'climate change statistics 2023'."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (max 20). Default: 10.",
                    "default": 10
                },
                "convert_html_to_markdown": {
                    "type": "boolean",
                    "description": "Convert search snippets from HTML to markdown. Default: true.",
                    "default": True
                },
                "search_engine": {
                    "type": "string",
                    "description": "Search engine to use. Options: 'auto', 'bing', 'duckduckgo'. Default: 'auto'.",
                    "enum": ["auto", "bing", "duckduckgo"],
                    "default": "auto"
                }
            },
            "required": ["query"]
        }
    }


def _process_ddg_url(url):
    """Process DuckDuckGo URLs to get the actual target URL."""
    try:
        import urllib.parse
        url_parts = urllib.parse.urlparse(url)
        
        # Case 1: Traditional uddg parameter format
        if 'uddg' in url_parts.query:
            query_parts = urllib.parse.parse_qs(url_parts.query)
            extracted_url = query_parts.get('uddg', [''])[0]
            if extracted_url:
                return extracted_url
                
        # Case 2: Advertising/redirect y.js format
        elif 'y.js' in url_parts.path:
            query_parts = urllib.parse.parse_qs(url_parts.query)
            # Try ad_domain first
            if 'ad_domain' in query_parts and query_parts['ad_domain'][0]:
                return f"https://{query_parts['ad_domain'][0]}"
            # Then try du parameter
            elif 'du' in query_parts and query_parts['du'][0]:
                return query_parts['du'][0]
            # Try other known parameters
            for param in ['u', 'l']:
                if param in query_parts and query_parts[param][0]:
                    return query_parts[param][0]
        
        # Case 3: Direct URL
        elif url.startswith('http'):
            return url
            
    except Exception as e:
        print(f"Error processing DuckDuckGo URL: {str(e)}")
    
    # Default to original URL if all else fails
    return url


def _process_bing_url(url):
    """Process Bing URLs to get the actual target URL."""
    try:
        import urllib.parse
        parsed_url = urllib.parse.urlparse(url)
        
        # Check if it's a Bing redirect URL
        if parsed_url.netloc == 'www.bing.com' and parsed_url.path == '/ck/a':
            # Try to extract the actual URL from Bing's redirect
            query_dict = urllib.parse.parse_qs(parsed_url.query)
            if 'u' in query_dict:
                # Bing stores the actual URL in the 'u' parameter, often base64 encoded
                import base64
                try:
                    # Try to decode if it's base64
                    real_url = base64.b64decode(query_dict['u'][0]).decode('utf-8')
                    return real_url
                except Exception:
                    # If not base64, just use it directly
                    return query_dict['u'][0]
            
            # Try other known redirect parameters
            for param in ['purl', 'r']:
                if param in query_dict:
                    return query_dict[param][0]
    
    except Exception as e:
        print(f"Error processing Bing URL: {str(e)}")
    
    # Default to original URL if all else fails
    return url


async def handle_web_search(arguments: dict) -> List[TextContent]:
    """Handle performing a web search using direct HTML scraping with anti-detection measures."""
    query = arguments.get("query")
    num_results = min(arguments.get("num_results", 10), 20)  # Cap at 20 results max
    convert_html_to_markdown = arguments.get("convert_html_to_markdown", True)
    search_engine = arguments.get("search_engine", "auto").lower()
    engine_warning = None

    if not query:
        raise ValueError("Search query must be provided")

    # Validate search engine parameter
    valid_engines = ["auto", "bing", "duckduckgo"]
    if search_engine not in valid_engines:
        if search_engine == "google":
            engine_warning = "Warning: Google search engine is no longer supported due to blocking automated requests. Falling back to 'auto' mode."
        else:
            engine_warning = f"Warning: Unsupported search engine '{search_engine}'. Valid options are: {', '.join(valid_engines)}. Falling back to 'auto' mode."
        print(engine_warning)
        search_engine = "auto"  # Default to auto if invalid

    # Create a list of common user agents to rotate through
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    ]

    # Use a random user agent
    user_agent = random.choice(user_agents)

    # Set up params for the request
    params = {
        "q": query,
        "num": num_results + 5,  # Request a few more results than needed
        "hl": "en",              # Language hint
        "gl": "us",              # Geolocation hint (helps avoid redirect to country-specific sites)
    }

    # Set up headers to more closely mimic a real browser
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.skydeck.ai/",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }

    # Define search engines configurations
    search_engines = [
        {
            "name": "DuckDuckGo HTML",
            "id": "duckduckgo",
            "url": "https://html.duckduckgo.com/html/",
            "params": {"q": query},
            "headers": {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://duckduckgo.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            "result_selector": [
                ".web-result",
                ".result:not(.result--ad)", 
                ".results_links:not(.result--ad)",
                ".result"
            ],
            "title_selector": [
                ".result__title",
                ".result__a",
                "h2",
                ".result__title a"
            ],
            "link_selector": [
                "a.result__a", 
                "a.result__url",
                ".result__title a",
                "a[href^='http']"
            ],
            "snippet_selector": [
                ".result__snippet", 
                ".result__snippet p", 
                ".result__desc",
                ".result__body",
                ".snippet"
            ]
        },
        {
            "name": "Bing",
            "id": "bing",
            "url": "https://www.bing.com/search",
            "params": {"q": query, "count": num_results},
            "headers": {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://www.bing.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            "result_selector": [
                ".b_algo",
                "li.b_algo",
                ".b_results > li:not(.b_ad)",
                "ol#b_results > li"
            ],
            "title_selector": [
                "h2",
                ".b_title",
                "h2 a",
                "a"
            ],
            "link_selector": [
                "h2 a",
                "a.tilk",
                "cite",
                ".b_attribution > cite",
                "a[href^='http']"
            ],
            "snippet_selector": [
                ".b_caption p",
                ".b_snippet",
                ".b_richcard",
                ".b_caption",
                ".b_algoSlug"
            ]
        }
    ]

    # Filter engines based on user preference
    if search_engine != "auto":
        filtered_engines = [engine for engine in search_engines if engine["id"] == search_engine]
        if filtered_engines:
            search_engines = filtered_engines
        # If no matching engine found, keep the original list (fallback to auto)

    # Track URLs we've already seen to prevent duplicates
    seen_urls = set()

    # Try each search engine until one works
    for engine in search_engines:
        try:
            print(f"Trying search with {engine['name']}...")

            # Add a small delay to avoid rate limiting
            time.sleep(random.uniform(0.5, 1.5))

            # Make the request
            response = requests.get(
                engine["url"],
                params=engine["params"],
                headers=engine["headers"],
                timeout=15
            )

            # Check if the response was successful
            if response.status_code == 200:
                # Parse the HTML response
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    search_results = []

                    # Special handling for DuckDuckGo which uses different URL structure
                    is_ddg = engine["name"] == "DuckDuckGo HTML"

                    # Convert single selector to list for consistent handling
                    result_selectors = engine["result_selector"]
                    if isinstance(result_selectors, str):
                        result_selectors = [result_selectors]
                        
                    # Try each result selector until we find results
                    result_elements = []
                    for selector in result_selectors:
                        result_elements = soup.select(selector)
                        if result_elements:
                            print(f"Found {len(result_elements)} results with selector '{selector}'")
                            break
                    
                    print(f"Found {len(result_elements)} potential results with {engine['name']}")

                    for result in result_elements:
                        if len(search_results) >= num_results:
                            break

                        # Try all title selectors
                        title_selectors = engine["title_selector"]
                        if isinstance(title_selectors, str):
                            title_selectors = [title_selectors]
                            
                        title_element = None
                        for selector in title_selectors:
                            title_element = result.select_one(selector)
                            if title_element:
                                break
                        
                        # Try all link selectors
                        link_selectors = engine["link_selector"]
                        if isinstance(link_selectors, str):
                            link_selectors = [link_selectors]
                            
                        link_element = None
                        for selector in link_selectors:
                            link_element = result.select_one(selector)
                            if link_element and 'href' in link_element.attrs:
                                break
                        
                        # Try all snippet selectors
                        snippet_selectors = engine["snippet_selector"]
                        if isinstance(snippet_selectors, str):
                            snippet_selectors = [snippet_selectors]
                            
                        snippet_element = None
                        for selector in snippet_selectors:
                            snippet_element = result.select_one(selector)
                            if snippet_element:
                                break

                        # If we couldn't find link or title, try looking for any anchor tag with text
                        if not link_element and not title_element:
                            for anchor in result.find_all('a', href=True):
                                if anchor.text.strip() and len(anchor.text.strip()) > 3:
                                    link_element = anchor
                                    title_element = anchor
                                    break

                        if title_element and link_element and 'href' in link_element.attrs:
                            # Process URL
                            url = link_element['href']
                            
                            # Process URL based on search engine
                            if is_ddg:
                                url = _process_ddg_url(url)
                            elif engine["id"] == "bing":
                                url = _process_bing_url(url)
                            
                            # Skip duplicate URLs
                            canonical_url = url.split('?')[0].rstrip('/')  # Remove query params and trailing slash for comparison
                            if canonical_url in seen_urls:
                                continue
                            seen_urls.add(canonical_url)

                            # Ensure URL is valid
                            if not url or not url.startswith('http'):
                                continue

                            # Get title and snippet
                            title = title_element.text.strip()
                            snippet = snippet_element.text.strip() if snippet_element else "No description available"

                            # Add to results if we have valid data
                            if title:
                                search_results.append({
                                    "title": title,
                                    "link": url,
                                    "snippet": snippet
                                })

                    # If we found results, format and return them
                    if search_results:
                        print(f"Success! Found {len(search_results)} results with {engine['name']}")
                        return _format_search_results(query, search_results, convert_html_to_markdown, engine["name"], engine_warning)

                except Exception as parse_error:
                    print(f"Error parsing {engine['name']} results: {str(parse_error)}")
                    # Continue to the next engine
            else:
                print(f"{engine['name']} returned status code: {response.status_code}")

        except Exception as e:
            print(f"Error with {engine['name']}: {str(e)}")
            # Continue to the next engine

    # If all engines fail, try a last-resort approach: extract any links from the last response
    try:
        if 'response' in locals() and response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            print("Attempting emergency link extraction...")
            emergency_results = []

            # Look for common result containers first
            potential_containers = [
                # Common search result containers
                soup.select("div.g, div.b_algo, .result, .web-result, .results_links, li[data-bm], div[data-hveid]"),
                # Any div with title-like content
                soup.select("div:has(h1), div:has(h2), div:has(h3), div:has(h4)"),
                # Main content areas
                soup.select("main, #main, #content, .content, #results, .results"),
                # Fallback to any link with reasonable text
                soup.select("a[href^='http']")
            ]

            # Process each container type in order until we find enough results
            for container_set in potential_containers:
                if container_set and len(emergency_results) < num_results:
                    for container in container_set:
                        # For containers, look for links inside
                        if container.name != 'a':
                            links = container.select("a[href^='http']") or []
                            # Process each link in the container
                            for link in links:
                                url = link.get('href', '')
                                title = link.text.strip()
                                
                                # Skip navigation links or empty links
                                if not url or not title or len(title) < 5:
                                    continue
                                    
                                # Skip search engine internal links
                                if any(s in url for s in ['google.com/search', 'bing.com/search', 'duckduckgo.com']):
                                    continue
                                
                                # Skip duplicate URLs
                                canonical_url = url.split('?')[0].rstrip('/')
                                if canonical_url in seen_urls:
                                    continue
                                seen_urls.add(canonical_url)
                                
                                # Process URL based on domain
                                if 'bing.com' in url:
                                    url = _process_bing_url(url)
                                elif 'duckduckgo.com' in url:
                                    url = _process_ddg_url(url)
                                
                                # Find snippet text near the link if possible
                                snippet = "No description available"
                                # Try to get snippet from surrounding paragraph or div
                                parent = link.parent
                                if parent:
                                    # Look for sibling paragraphs or divs
                                    sibling = parent.find_next_sibling(['p', 'div', 'span'])
                                    if sibling and sibling.text.strip():
                                        snippet = sibling.text.strip()
                                    # Or try parent's text excluding the link text
                                    elif parent.name in ['p', 'div', 'span'] and len(parent.text) > len(title):
                                        snippet_text = parent.text.replace(title, '').strip()
                                        if snippet_text:
                                            snippet = snippet_text
                                
                                emergency_results.append({
                                    "title": title,
                                    "link": url,
                                    "snippet": snippet
                                })
                                
                                if len(emergency_results) >= num_results:
                                    break
                        else:
                            # Process direct link
                            url = container.get('href', '')
                            title = container.text.strip()
                            
                            # Skip invalid links
                            if not url or not title or len(title) < 5:
                                continue
                                
                            # Skip search engine internal links
                            if any(s in url for s in ['google.com/search', 'bing.com/search', 'duckduckgo.com']):
                                continue
                            
                            # Skip duplicate URLs
                            canonical_url = url.split('?')[0].rstrip('/')
                            if canonical_url in seen_urls:
                                continue
                            seen_urls.add(canonical_url)
                            
                            emergency_results.append({
                                "title": title,
                                "link": url,
                                "snippet": "No description available"
                            })
                            
                            if len(emergency_results) >= num_results:
                                break
                        
                        if len(emergency_results) >= num_results:
                            break

            if emergency_results:
                print(f"Found {len(emergency_results)} emergency results by extracting links")
                return _format_search_results(query, emergency_results, convert_html_to_markdown, "Emergency Links", engine_warning)
    except Exception as e:
        print(f"Error in emergency link extraction: {str(e)}")

    # If all search methods fail, provide helpful fallback information
    print("All search methods failed, providing search fallback")
    return _provide_search_fallback(query, engine_warning)


def _format_search_results(query: str, search_results: list, convert_html_to_markdown: bool, engine_name: str = None, engine_warning: str = None) -> List[TextContent]:
    """Format search results into markdown."""
    formatted_results = ["# Web Search Results\n\n"]
    formatted_results.append(f"**Query:** {query}\n\n")

    if engine_warning:
        formatted_results.append(f"**{engine_warning}**\n\n")

    if engine_name:
        formatted_results.append(f"**Source:** {engine_name}\n\n")

    for i, item in enumerate(search_results, 1):
        title = item.get("title", "No title")
        link = item.get("link", "")
        snippet = item.get("snippet", "No description available")

        # Convert HTML in snippet to markdown if requested
        if convert_html_to_markdown:
            try:
                import html2text
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0  # Don't wrap text

                # Remove HTML tags from title and snippet
                title = h.handle(title) if '<' in title else title
                snippet = h.handle(snippet) if '<' in snippet else snippet
            except ImportError:
                # Continue without conversion if html2text is not available
                # Just strip basic HTML tags as a fallback
                import re
                title = re.sub(r'<[^>]*>', '', title)
                snippet = re.sub(r'<[^>]*>', '', snippet)

        formatted_results.append(f"## {i}. {title}\n")
        formatted_results.append(f"**URL:** {link}\n\n")
        formatted_results.append(f"{snippet}\n\n---\n\n")

    return [TextContent(
        type="text",
        text="".join(formatted_results)
    )]


def _provide_search_fallback(query: str, engine_warning: str = None) -> List[TextContent]:
    """Provide a useful fallback when search fails."""
    # Create a helpful response with suggestions for alternative approaches
    formatted_results = ["# Web Search Results\n\n"]
    formatted_results.append(f"**Query:** {query}\n\n")
    
    if engine_warning:
        formatted_results.append(f"**{engine_warning}**\n\n")
        
    formatted_results.append("I couldn't retrieve search results at this time.\n\n")

    # Add explanation about limitations
    formatted_results.append("## Why search might be unavailable\n\n")
    formatted_results.append("Web search APIs often have restrictions on automated access, which can cause searches to fail. When this happens, it's better to:\n\n")
    formatted_results.append("1. Try a different search engine (Bing or DuckDuckGo which are more reliable for automated access)\n")
    formatted_results.append("2. Visit specific authoritative sites directly\n")
    formatted_results.append("3. Try the search again later, or with different terms\n")

    return [TextContent(
        type="text",
        text="".join(formatted_results)
    )]
