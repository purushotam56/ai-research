import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
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

def scrape_url(url):
    """
    Scrape URL and extract meaningful content.
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
        
        # Extract title - with fallback options
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
        
        # Extract main content
        # Try to find main content areas
        content_div = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile('content|main|body', re.I))
        
        if content_div:
            text = content_div.get_text()
        else:
            text = soup.get_text()
        
        # Clean up text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        # Remove extra whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        return {
            'success': True,
            'title': title,
            'content': content,
            'url': url,
            'source_type': 'url'
        }
    
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Failed to fetch URL: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Error processing URL: {str(e)}'}

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
    Extract meaningful content from raw text.
    Removes excessive whitespace, empty lines, etc.
    """
    # First, remove excessive whitespace
    content = '\n'.join(line.rstrip() for line in raw_content.split('\n'))
    
    # Remove multiple consecutive blank lines
    while '\n\n\n' in content:
        content = content.replace('\n\n\n', '\n\n')
    
    # Clean up content (but keep more than before to avoid empty results)
    content = content.strip()
    
    # Split into paragraphs to filter very short ones
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    # Only filter out extremely short single-word lines (less than 5 chars)
    # But keep normal short lines that are part of the content
    filtered_paragraphs = []
    for para in paragraphs:
        # Keep paragraph if it has multiple lines or is reasonably long
        lines_in_para = para.split('\n')
        
        # If it's a multi-line paragraph, keep it regardless of length
        if len(lines_in_para) > 1:
            filtered_paragraphs.append(para)
        # If it's a single line, only filter if it's extremely short
        elif len(para) > 5:
            filtered_paragraphs.append(para)
        # For very short lines (< 5 chars), only filter if it's a single character
        elif len(para) > 1:
            filtered_paragraphs.append(para)
    
    content = '\n\n'.join(filtered_paragraphs)
    
    # If no content after filtering, return original content to avoid empty result
    if not content.strip():
        content = raw_content.strip()
    
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
