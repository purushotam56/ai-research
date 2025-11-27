import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
from pypdf import PdfReader
import re

def is_valid_url(url):
    """Validate if string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def extract_same_domain_links(soup, base_url, max_links=20):
    """
    Extract up to max_links from the same domain as base_url.
    Only extracts links, does NOT scrape them (that's done by caller).
    """
    try:
        base_domain = urlparse(base_url).netloc
        found_links = set()
        
        # Find all links in the page
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            
            if not href or href.startswith('#') or href.startswith('javascript:') or '@' in href:
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            link_domain = urlparse(absolute_url).netloc
            
            # Only include links from same domain and valid URLs (not emails)
            if link_domain == base_domain and absolute_url not in found_links and '@' not in absolute_url:
                found_links.add(absolute_url)
                
                # Stop when we have max_links
                if len(found_links) >= max_links:
                    break
        
        return list(found_links)
    except Exception as e:
        print(f"[URL] Error extracting links: {str(e)}")
        return []

def _extract_title_from_soup(soup, url):
    """Extract title from soup with multiple fallback options"""
    title = None
    
    # Try different methods to get the title
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    
    # Try meta og:title
    if not title or title == "":
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title.get('content').strip()
    
    # Try meta name="title"
    if not title or title == "":
        meta_title = soup.find('meta', attrs={'name': 'title'})
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
    
    # Try h1 tag
    if not title or title == "":
        h1 = soup.find('h1')
        if h1 and h1.get_text():
            title = h1.get_text().strip()
    
    # Fallback to domain name
    if not title or title == "":
        title = urlparse(url).netloc or "Webpage"
    
    # Ensure title is never None or empty
    if not title:
        title = "Webpage"
    
    return title

def extract_logical_sections(text):
    """
    Extract logical sections from text based on visual structure.
    Detects: MAIN SECTIONS (all caps) → Subsections (Title Case) → Content
    
    Returns: list of dicts with {section_name, subsection_name, content}
    """
    sections = []
    lines = text.split('\n')
    
    current_section = None
    current_subsection = None
    current_content = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            if current_content and len(current_content) > 1:  # Keep some empty lines for spacing
                current_content.append('')
            continue
        
        # Detect MAIN SECTION (ALL CAPS, no leading numbers in first word)
        is_main_section = False
        if line_stripped.isupper() and len(line_stripped) > 3:
            # Check it's not a list item like "01. Technical Expertise"
            first_word = line_stripped.split()[0]
            if not first_word[0].isdigit():
                is_main_section = True
        
        if is_main_section:
            # Save previous section/subsection
            if current_section and current_content:
                content_text = '\n'.join(current_content).strip()
                if content_text and len(content_text) > 20:
                    sections.append({
                        'section_name': current_section,
                        'subsection_name': current_subsection,
                        'content': content_text
                    })
            
            current_section = line_stripped
            current_subsection = None
            current_content = []
        
        # Detect SUBSECTION (Title Case with 2-5 words, not all caps, not a person name)
        elif current_section:
            # Check if looks like subsection header
            is_subsection = False
            if line_stripped[0].isupper() and not line_stripped.isupper():
                word_count = len(line_stripped.split())
                if 1 <= word_count <= 5:
                    # Check if mostly capitalized (title case pattern)
                    cap_words = sum(1 for w in line_stripped.split() if w[0].isupper())
                    if cap_words >= word_count * 0.6:  # Most words start with capital
                        # Avoid person names (check if it's a common title word pattern)
                        common_title_words = ['team', 'team', 'section', 'list', 'group', 'developer', 'manager', 
                                            'architect', 'consultant', 'engineer', 'executive', 'associate',
                                            'leadership', 'management', 'sales', 'recruitment', 'workday',
                                            'product', 'sharepoint', 'mulesoft', 'salesforce', 'servicenow',
                                            'other', 'dynamic']
                        line_lower = line_stripped.lower()
                        if any(title_word in line_lower for title_word in common_title_words):
                            is_subsection = True
            
            if is_subsection:
                # Save previous subsection
                if current_content:
                    content_text = '\n'.join(current_content).strip()
                    if content_text and len(content_text) > 20:
                        sections.append({
                            'section_name': current_section,
                            'subsection_name': current_subsection,
                            'content': content_text
                        })
                
                current_subsection = line_stripped
                current_content = []
            else:
                # Regular content line
                current_content.append(line_stripped)
        else:
            # No section yet, accumulate as content
            current_content.append(line_stripped)
    
    # Save final section
    if current_section and current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text and len(content_text) > 20:
            sections.append({
                'section_name': current_section,
                'subsection_name': current_subsection,
                'content': content_text
            })
    
    return sections

def scrape_single_url(url):
    """
    Scrape a single URL and extract meaningful content.
    Returns: dict with title, content, and metadata
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Extract title
        title = _extract_title_from_soup(soup, url)
        
        # Extract main content - try multiple strategies
        content_div = None
        
        # Strategy 1: Try <main> tag
        content_div = soup.find('main')
        if content_div:
            text = content_div.get_text()
            if len(text.strip()) < 200:  # If main is too small, try other sources
                content_div = None
        
        # Strategy 2: Try <article> tag
        if not content_div:
            content_div = soup.find('article')
            if content_div:
                text = content_div.get_text()
                if len(text.strip()) < 200:
                    content_div = None
        
        # Strategy 3: Try WordPress site blocks (wp-site-blocks or wp-block-group)
        if not content_div:
            content_div = soup.find('div', class_=lambda x: x and 'wp-site-blocks' in (x if isinstance(x, str) else ' '.join(x)))
        
        # Strategy 4: Try common content divs
        if not content_div:
            content_div = soup.find('div', class_=re.compile('content|main|body|post-content|entry-content', re.I))
        
        # Strategy 5: Use body as fallback and remove header/footer/nav
        if not content_div:
            content_div = soup.find('body')
        
        if content_div:
            text = content_div.get_text()
        else:
            text = soup.get_text()
        
        # Clean up text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        # Remove extra whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove footer/contact sections at the end
        # Look for common footer section markers
        footer_markers = ['Contact Info', 'Contact Us', 'Privacy Policy']
        
        for marker in footer_markers:
            if marker in content:
                marker_pos = content.find(marker)
                # Only consider if it's in the last 30% of content (to skip navigation "Contact Us")
                if marker_pos > len(content) * 0.7:
                    # Find the last paragraph break (double newline) before the marker
                    last_para = content.rfind('\n\n', max(0, marker_pos - 1000), marker_pos)
                    if last_para < 0:
                        # If no double newline, find the last single newline
                        last_para = content.rfind('\n', max(0, marker_pos - 500), marker_pos)
                    
                    if last_para > len(content) * 0.5:  # Ensure we keep at least 50% of content
                        content = content[:last_para].rstrip()
                    break
        
        # Extract logical sections from cleaned content
        sections = extract_logical_sections(content)
        
        return {
            'success': True,
            'title': title,
            'content': content,
            'sections': sections,  # NEW: Include logical sections
            'url': url,
            'source_type': 'url'
        }
    
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Failed to fetch URL: {str(e)}', 'url': url}
    except Exception as e:
        return {'success': False, 'error': f'Error processing URL: {str(e)}', 'url': url}

def scrape_url(url, progress_callback=None):
    """
    Scrape URL and discover related links from same domain.
    Groups all content under a single resource.
    
    Args:
        url: The initial URL to scrape
        progress_callback: Optional callback function(event_type, data) for progress tracking
            - event_type: 'links_discovered', 'scraping_start', 'scraping_progress', 'scraping_complete', 'scraping_error'
            - data: dict with relevant info
    
    Returns: dict with combined content from all scraped URLs
    """
    try:
        if progress_callback:
            progress_callback('scraping_start', {'url': url})
        
        # First, scrape the main URL
        main_result = scrape_single_url(url)
        
        if not main_result['success']:
            if progress_callback:
                progress_callback('scraping_error', {'error': main_result['error'], 'url': url})
            return main_result
        
        # Now discover related links from the main URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract up to 10 related links from same domain
        related_links = extract_same_domain_links(soup, url, max_links=10)
        
        # IMPORTANT: Remove the main URL from related_links to avoid duplicates
        related_links = [link for link in related_links if link != url]
        
        if progress_callback:
            progress_callback('links_discovered', {'count': len(related_links), 'links': related_links})
        
        # Scrape all discovered links (but NOT links discovered from those links)
        all_urls = [url] + related_links  # Include main URL in the list
        all_content = []
        
        for idx, scrape_url_item in enumerate(all_urls):
            # Skip if it's the main URL (already scraped)
            if scrape_url_item == url:
                all_content.append({
                    'url': main_result['url'],
                    'title': main_result['title'],
                    'content': main_result['content']
                })
                continue
            
            # Scrape this related link
            if progress_callback:
                progress_callback('scraping_progress', {
                    'current': idx + 1,
                    'total': len(all_urls),
                    'url': scrape_url_item,
                    'status': 'scraping'
                })
            
            link_result = scrape_single_url(scrape_url_item)
            
            if link_result['success']:
                all_content.append({
                    'url': link_result['url'],
                    'title': link_result['title'],
                    'content': link_result['content'],
                    'sections': link_result.get('sections')  # Include sections
                })
                
                if progress_callback:
                    progress_callback('scraping_progress', {
                        'current': idx + 1,
                        'total': len(all_urls),
                        'url': scrape_url_item,
                        'status': 'success'
                    })
            else:
                if progress_callback:
                    progress_callback('scraping_progress', {
                        'current': idx + 1,
                        'total': len(all_urls),
                        'url': scrape_url_item,
                        'status': 'failed',
                        'error': link_result['error']
                    })
        
        # Group content by URL (NOT merged)
        url_grouped = {}
        urls_data = []  # Track main vs related URLs
        
        for idx, item in enumerate(all_content):
            url_grouped[item['url']] = {
                'title': item['title'],
                'content': item['content'],
                'sections': item.get('sections')  # Include sections
            }
            # First URL is main, rest are related
            urls_data.append({
                'url': item['url'],
                'title': item['title'],
                'is_main': idx == 0,
                'is_related': idx > 0
            })
        
        # Also create merged version for search/vector store
        combined_content = "\n\n---\n\n".join([
            f"## {item['title']}\nSource: {item['url']}\n\n{item['content']}"
            for item in all_content
        ])
        
        main_title = main_result['title']
        
        if progress_callback:
            progress_callback('scraping_complete', {
                'total_urls': len(all_urls),
                'successful': sum(1 for item in all_content),
                'main_url': url
            })
        
        return {
            'success': True,
            'title': main_title,
            'content': combined_content,
            'url': url,
            'source_type': 'url_group',
            'urls_scraped': len(all_urls),
            'related_urls': related_links,
            'url_grouped_content': url_grouped,  # URL-wise grouped data
            'urls_data': urls_data,  # NEW: Track main vs related URLs
            'sections': all_content[0].get('sections') if all_content else None  # Sections from main URL
        }
    
    except Exception as e:
        error_msg = f'Error processing URL group: {str(e)}'
        if progress_callback:
            progress_callback('scraping_error', {'error': error_msg})
        return {'success': False, 'error': error_msg}

def process_pdf_file(file_path):
    """
    Process PDF file and extract text.
    Returns: dict with title, content, and metadata
    """
    try:
        filename = os.path.basename(file_path)
        
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            # Extract text from all pages
            text = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            
            content = '\n\n'.join(text)
            
            # Clean up content
            content = re.sub(r'\n\s*\n', '\n\n', content)
            
            return {
                'success': True,
                'title': filename,
                'content': content,
                'filename': filename,
                'num_pages': num_pages,
                'source_type': 'file'
            }
    
    except Exception as e:
        return {'success': False, 'error': f'Error processing PDF: {str(e)}'}

def process_text_file(file_path):
    """
    Process text file (.txt, .md, etc).
    Returns: dict with title, content, and metadata
    """
    try:
        filename = os.path.basename(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        return {
            'success': True,
            'title': filename,
            'content': content,
            'filename': filename,
            'source_type': 'file'
        }
    
    except Exception as e:
        return {'success': False, 'error': f'Error processing text file: {str(e)}'}

def extract_meaningful_content(raw_content, max_chars=None):
    """
    Extract meaningful content from raw text intelligently.
    AGGRESSIVELY removes: nav, menus, footers, contact forms, emails, phone numbers.
    Keeps only actual body content.
    """
    import re
    
    # Split by double newlines to identify paragraphs
    paragraphs = raw_content.split('\n\n')
    
    meaningful_paragraphs = []
    
    # Aggressive noise patterns
    noise_keywords = {
        # Navigation
        'homeabout', 'services', 'pricing', 'careers', 'case studies',
        'contact us', 'privacy', 'terms', 'cookie', 'subscribe',
        'follow us', 'social', 
        # Contact
        'call:', 'email:', 'phone:', 'address:', 'hours:',
        'facebook', 'linkedin', 'twitter', 'instagram', 'youtube',
        # Forms
        'first name', 'last name', 'middle name', 'employment type',
        'full time', 'contract', 'onboarding', 'form submission',
        'required field', 'delta first',
    }
    
    for para in paragraphs:
        para = para.strip()
        
        # Skip empty paragraphs
        if not para:
            continue
        
        # Skip very short lines (likely headers/nav)
        if len(para) < 8:
            continue
        
        # BLOCK: Email addresses
        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', para):
            continue
        
        # BLOCK: Phone numbers
        if re.search(r'\+61|\+1\s?\(|\(\d{3}\)|\d{3}-\d{3}-\d{4}', para):
            continue
        
        # BLOCK: Form fields
        if any(keyword in para.lower() for keyword in ['first name', 'last name', 'email address',
                                                         'phone number', 'employment type',
                                                         'onboarding form', 'required field',
                                                         'submit button', 'your message']):
            continue
        
        para_lower = para.lower()
        
        # BLOCK: Navigation-only content
        if para.count('|') > 2 or para.count('/') > 3:
            if all(len(x.strip()) < 20 for x in para.split('|') + para.split('/')):
                continue
        
        # BLOCK: Heavy contact/footer content
        noise_count = sum(1 for noise in noise_keywords if noise in para_lower)
        if noise_count > 3 and len(para) < 150:
            continue
        
        # BLOCK: Copyright/footer markers
        if any(marker in para for marker in ['©', 'copyright', '™', '®']):
            if 'all rights reserved' in para_lower or 'powered by' in para_lower:
                continue
        
        # BLOCK: Contact page patterns
        if any(pattern in para_lower for pattern in 
               ['get in touch', 'contact information', 'office address', 'visit us',
                'australia:', 'india:', 'nsw', 'level 1', 'level 2',
                'banks ave', 'eastgardens', 'sydney']):
            continue
        
        # BLOCK: Single word navigation items
        if len(para.split()) == 1 and para in ['Contact', 'Services', 'About', 'Home', 
                                                  'Menu', 'Login', 'Register', 'Blog', 'More']:
            continue
        
        # KEEP: Everything else
        meaningful_paragraphs.append(para)
    
    # Join back together
    content = '\n\n'.join(meaningful_paragraphs)
    
    # Clean up excessive whitespace
    content = '\n'.join(line.rstrip() for line in content.split('\n'))
    while '\n\n\n' in content:
        content = content.replace('\n\n\n', '\n\n')
    
    content = content.strip()
    
    # If we filtered out too much, return more of the original but still cleaned
    if len(content) < 200:
        # Fall back: keep substantial lines only
        lines = raw_content.split('\n')
        kept_lines = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 8:  # Keep only substantial lines
                # Skip obvious junk
                if any(x in line.lower() for x in ['first name', 'last name', 'email address',
                                                     'phone number', '@', '+61', '+1']):
                    continue
                kept_lines.append(line)
        content = '\n'.join(kept_lines)
    
    if max_chars and len(content) > max_chars:
        content = content[:max_chars] + '...'
    
    return content

def get_file_extension(filename):
    """Get file extension"""
    return os.path.splitext(filename)[1].lower()

def supported_file_type(filename):
    """Check if file type is supported"""
    supported = ['.pdf', '.txt', '.md', '.docx']
    return get_file_extension(filename) in supported
