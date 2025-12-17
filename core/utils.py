"""
Utility functions for livehttpx
"""

import re
import socket
import time
import random
import ipaddress
from typing import List, Set, Optional, Dict, Any
import urllib.parse
from .exceptions import InputError


class Color:
    """ANSI color codes"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


def validate_domain(domain: str) -> bool:
    """Validate domain format"""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))


def validate_ip(ip: str) -> bool:
    """Validate IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def extract_host_from_url(url: str) -> str:
    """Extract host from URL"""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc:
            return parsed.netloc.split(':')[0]
        return url.split('/')[0]
    except:
        return url


def clean_domain(domain: str) -> str:
    """Clean domain string"""
    domain = domain.strip()
    
    # Remove protocol
    if '://' in domain:
        domain = domain.split('://')[-1]
    
    # Remove path and query
    domain = domain.split('/')[0]
    
    # Remove port
    domain = domain.split(':')[0]
    
    # Remove wildcards
    domain = domain.replace('*.', '')
    
    # Remove trailing dots
    domain = domain.rstrip('.')
    
    return domain.lower()


def parse_subdomains_from_file(filename: str) -> List[str]:
    """Parse subdomains from file"""
    domains = set()
    
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Clean the domain
                domain = clean_domain(line)
                
                # Validate
                if validate_domain(domain):
                    domains.add(domain)
                else:
                    # Try to extract domain from URL
                    extracted = extract_host_from_url(line)
                    if extracted != line and validate_domain(extracted):
                        domains.add(extracted)
                    else:
                        print(f"[!] Line {line_num}: Invalid domain format: {line}")
        
        if not domains:
            raise InputError(f"No valid domains found in file: {filename}")
        
        return list(domains)
        
    except FileNotFoundError:
        raise InputError(f"File not found: {filename}")
    except Exception as e:
        raise InputError(f"Error reading file {filename}: {e}")


def get_ip_address(hostname: str) -> Optional[str]:
    """Get IP address for hostname"""
    try:
        return socket.gethostbyname(hostname)
    except:
        return None


def extract_title(html: str) -> str:
    """Extract title from HTML"""
    try:
        # Clean HTML comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Look for title tag
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)
            title = re.sub(r'[\r\n\t]', '', title)
            return title[:150]
        
        # Try meta title as fallback
        meta_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\'](.*?)["\']', 
                             html, re.IGNORECASE)
        if meta_match:
            return meta_match.group(1).strip()[:150]
        
        # Try meta name="title"
        meta_match = re.search(r'<meta[^>]*name=["\']title["\'][^>]*content=["\'](.*?)["\']', 
                             html, re.IGNORECASE)
        if meta_match:
            return meta_match.group(1).strip()[:150]
        
    except:
        pass
    
    return ""


def format_size(size: int) -> str:
    """Format file size in human readable format"""
    if size == 0:
        return "0B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


def format_time(seconds: float) -> str:
    """Format time in human readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def detect_cms(html: str, headers: Dict[str, str]) -> str:
    """Detect CMS from response"""
    cms_patterns = {
        'WordPress': [
            r'wp-content', r'/wp-includes/', r'wordpress', r'wp-json',
            r'name="generator" content="WordPress'
        ],
        'Joomla': [
            r'/media/system/', r'/media/jui/', r'joomla',
            r'name="generator" content="Joomla'
        ],
        'Drupal': [
            r'/sites/all/', r'/modules/system/', r'drupal',
            r'name="Generator" content="Drupal'
        ],
        'Magento': [
            r'Magento', r'/skin/frontend/', r'/media/catalog/'
        ],
        'Shopify': [
            r'shopify', r'shopifycdn'
        ],
        'Ghost': [
            r'ghost', r'content="Ghost'
        ],
        'Wix': [
            r'wix', r'Wix.com Website Builder'
        ],
        'Squarespace': [
            r'squarespace', r'SS_COMMERCE'
        ],
        'Blogger': [
            r'blogger', r'Blogger'
        ],
        'TYPO3': [
            r'typo3', r'TYPO3'
        ],
    }
    
    content = html.lower() + ' ' + ' '.join(headers.values()).lower()
    
    for cms, patterns in cms_patterns.items():
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return cms
    
    return ""


def detect_waf(headers: Dict[str, str]) -> str:
    """Detect WAF from headers"""
    waf_indicators = {
        'Cloudflare': ['cloudflare', 'cf-ray', '__cfduid'],
        'CloudFront': ['x-amz-cf-id', 'cloudfront'],
        'Akamai': ['akamai', 'x-akamai'],
        'Sucuri': ['x-sucuri-id', 'sucuri'],
        'Incapsula': ['incap_ses', 'visid_incap'],
        'ModSecurity': ['mod_security'],
        'Barracuda': ['barracuda'],
        'FortiWeb': ['fortiweb'],
        'AWS WAF': ['x-aws-waf'],
        'Imperva': ['x-cdn', 'imperva'],
    }
    
    header_str = ' '.join(headers.keys()).lower() + ' ' + ' '.join(headers.values()).lower()
    
    for waf, indicators in waf_indicators.items():
        for indicator in indicators:
            if indicator.lower() in header_str:
                return waf
    
    return ""


def detect_cdn(headers: Dict[str, str]) -> str:
    """Detect CDN from headers"""
    cdn_indicators = {
        'Cloudflare': ['cloudflare', 'cf-ray'],
        'CloudFront': ['x-amz-cf-id'],
        'Akamai': ['x-akamai'],
        'Fastly': ['x-fastly'],
        'Google Cloud CDN': ['server-timing', 'google'],
        'Azure CDN': ['x-azure-ref'],
        'StackPath': ['server', 'stackpath'],
        'KeyCDN': ['x-edge-location', 'keycdn'],
        'BunnyCDN': ['bunnycdn', 'pullzone'],
        'CDN77': ['cdn77'],
    }
    
    header_str = ' '.join(headers.keys()).lower() + ' ' + ' '.join(headers.values()).lower()
    
    for cdn, indicators in cdn_indicators.items():
        for indicator in indicators:
            if indicator.lower() in header_str:
                return cdn
    
    return ""


def detect_forms(html: str) -> bool:
    """Detect if page has forms"""
    form_patterns = [
        r'<form[^>]*>',
        r'<input[^>]*type=["\']submit["\'][^>]*>',
        r'<button[^>]*type=["\']submit["\'][^>]*>',
    ]
    
    for pattern in form_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            return True
    
    return False


def detect_login_forms(html: str) -> bool:
    """Detect if page has login forms"""
    login_indicators = [
        r'type=["\']password["\']',
        r'name=["\']password["\']',
        r'id=["\']password["\']',
        r'login',
        r'signin',
        r'authenticate',
        r'password',
        r'username',
        r'user[\s_-]*name',
    ]
    
    if not detect_forms(html):
        return False
    
    for indicator in login_indicators:
        if re.search(indicator, html, re.IGNORECASE):
            return True
    
    return False


def detect_technologies(html: str, headers: Dict[str, str]) -> List[str]:
    """Detect technologies from response"""
    tech_patterns = {
        'React': [r'__NEXT_DATA__', r'react', r'react-dom'],
        'Vue.js': [r'vue', r'__vue__'],
        'Angular': [r'angular', r'ng-'],
        'jQuery': [r'jquery', r'jQuery'],
        'Bootstrap': [r'bootstrap', r'btn-'],
        'Tailwind CSS': [r'tailwind'],
        'Laravel': [r'laravel', r'csrf-token'],
        'Django': [r'django', r'csrftoken'],
        'Flask': [r'flask'],
        'Express.js': [r'express'],
        'Node.js': [r'node', r'x-powered-by: express'],
        'Nginx': [r'nginx'],
        'Apache': [r'Apache', r'httpd'],
        'PHP': [r'PHP/', r'.php'],
        'ASP.NET': [r'ASP.NET', r'__VIEWSTATE'],
        'Ruby on Rails': [r'rails', r'ruby'],
        'GraphQL': [r'graphql'],
        'REST API': [r'api', r'api/'],
        'WebSocket': [r'websocket', r'ws://', r'wss://'],
        'PWA': [r'service-worker', r'manifest.json'],
        'WordPress Plugin': [r'wp-content/plugins/'],
        'WooCommerce': [r'woocommerce'],
    }
    
    detected = set()
    content = html.lower() + ' ' + ' '.join(headers.values()).lower()
    
    for tech, patterns in tech_patterns.items():
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                detected.add(tech)
                break
    
    return list(detected)


def get_random_user_agent() -> str:
    """Get random user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
    ]
    
    return random.choice(user_agents)