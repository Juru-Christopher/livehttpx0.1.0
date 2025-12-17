"""
Main checking logic for livehttpx
"""

import concurrent.futures
import threading
import time
import random
import requests
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from .models import ScanResult, ScanConfig, ScanStats, TerminalInfo
from .utils import (
    get_ip_address, extract_title, detect_technologies,
    detect_cms, detect_waf, detect_cdn, detect_forms,
    detect_login_forms, get_random_user_agent, validate_ip
)
from .exceptions import TimeoutError, SSLError, NetworkError


class SubdomainChecker:
    """Main checker class"""
    
    def __init__(self, config: ScanConfig):
        self.config = config
        self.results: List[ScanResult] = []
        self.stats = ScanStats()
        self.stats.start_time = time.time()
        
        # Setup session
        self.session = requests.Session()
        if config.proxy:
            self.session.proxies = {
                'http': config.proxy,
                'https': config.proxy,
            }
        
        # Rate limiting
        self.last_request_time = 0
        self.rate_lock = threading.Lock()
        
        # User agents
        self.user_agents = [
            get_random_user_agent(),
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]
        self.current_user_agent = 0
    
    def _get_next_user_agent(self) -> str:
        """Get next user agent"""
        if self.config.custom_user_agent:
            return self.config.custom_user_agent
        
        if self.config.random_user_agent:
            return get_random_user_agent()
        
        agent = self.user_agents[self.current_user_agent]
        self.current_user_agent = (self.current_user_agent + 1) % len(self.user_agents)
        return agent
    
    def _rate_limit_wait(self):
        """Implement rate limiting"""
        if not self.config.rate_limit:
            return
        
        with self.rate_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < (1.0 / self.config.rate_limit):
                time.sleep((1.0 / self.config.rate_limit) - time_since_last)
            self.last_request_time = time.time()
    
    def _should_include_status(self, status: int) -> bool:
        """Check if status should be included based on config"""
        # Check exclude list
        if self.config.exclude_codes and status in self.config.exclude_codes:
            return False
        
        # Check include list (if specified, only include these)
        if self.config.include_codes and status not in self.config.include_codes:
            return False
        
        # Check match codes
        return status in self.config.match_codes
    
    def _extract_headers(self, response) -> Dict[str, str]:
        """Extract headers from response"""
        if not self.config.extract_headers:
            return {}
        
        headers = {}
        for key, value in response.headers.items():
            if key.lower() in ['server', 'x-powered-by', 'x-cdn', 'cf-ray', 'x-sucuri-id']:
                headers[key] = value
        return headers
    
    def _extract_cookies(self, response) -> Dict[str, str]:
        """Extract cookies from response"""
        if not self.config.extract_cookies:
            return {}
        
        cookies = {}
        for cookie in response.cookies:
            cookies[cookie.name] = cookie.value
        return cookies
    
    def check_host(self, host: str) -> Optional[ScanResult]:
        """Check a single host"""
        # Apply rate limiting
        self._rate_limit_wait()
        
        schemes = []
        if not self.config.only_https:
            schemes.append("http://")
        if not self.config.only_http:
            schemes.append("https://")
        
        for scheme in schemes:
            for attempt in range(self.config.retries + 1):
                try:
                    url = scheme + host
                    headers = {'User-Agent': self._get_next_user_agent()}
                    headers.update(self.config.custom_headers)
                    
                    start_time = time.time()
                    
                    response = self.session.get(
                        url,
                        timeout=self.config.timeout,
                        headers=headers,
                        verify=self.config.verify_ssl,
                        allow_redirects=self.config.follow_redirects
                    )
                    
                    response_time = time.time() - start_time
                    status_code = response.status_code
                    
                    if self._should_include_status(status_code):
                        # Get basic information
                        ip_address = get_ip_address(host)
                        title = extract_title(response.text)
                        
                        # Create result
                        result = ScanResult(
                            url=response.url if self.config.follow_redirects else url,
                            host=host,
                            status=status_code,
                            scheme=scheme.replace('://', ''),
                            title=title,
                            content_length=len(response.content),
                            server=response.headers.get('Server', ''),
                            ip_address=ip_address or '',
                            response_time=response_time,
                            headers=self._extract_headers(response),
                            cookies=self._extract_cookies(response)
                        )
                        
                        # Detect technologies if enabled
                        if self.config.tech_detection:
                            result.technologies = detect_technologies(
                                response.text, 
                                response.headers
                            )
                        
                        # Detect CMS if enabled
                        if self.config.detect_cms:
                            result.cms = detect_cms(response.text, response.headers)
                        
                        # Detect WAF if enabled
                        if self.config.detect_waf:
                            result.waf = detect_waf(response.headers)
                        
                        # Detect CDN if enabled
                        if self.config.detect_cdn:
                            result.cdn = detect_cdn(response.headers)
                        
                        # Detect forms if enabled
                        if self.config.find_forms:
                            result.has_form = detect_forms(response.text)
                        
                        # Detect login forms if enabled
                        if self.config.find_logins:
                            result.has_login = detect_login_forms(response.text)
                        
                        return result
                    
                except requests.exceptions.SSLError:
                    # Try without SSL verification as fallback
                    if self.config.verify_ssl and scheme == "https://":
                        try:
                            response = self.session.get(
                                url,
                                timeout=self.config.timeout,
                                headers=headers,
                                verify=False,
                                allow_redirects=self.config.follow_redirects
                            )
                            if self._should_include_status(response.status_code):
                                title = extract_title(response.text)
                                return ScanResult(
                                    url=response.url if self.config.follow_redirects else url,
                                    host=host,
                                    status=response.status_code,
                                    scheme='https',
                                    title=title,
                                    content_length=len(response.content),
                                    server=response.headers.get('Server', '')
                                )
                        except:
                            continue
                    continue
                except requests.exceptions.Timeout:
                    if attempt < self.config.retries:
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                except (requests.exceptions.ConnectionError,
                       requests.exceptions.RequestException):
                    continue
                except Exception:
                    continue
        
        return None
    
    def run_checks(self, hosts: List[str], 
                  progress_callback=None) -> List[ScanResult]:
        """Run checks on all hosts"""
        self.stats.total_checked = len(hosts)
        
        # Sort hosts by length (shorter first for quicker checks)
        hosts.sort(key=lambda x: len(x))
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_workers
        ) as executor:
            future_to_host = {
                executor.submit(self.check_host, host): host 
                for host in hosts
            }
            
            for future in concurrent.futures.as_completed(future_to_host):
                result = future.result()
                
                if result:
                    self.results.append(result)
                    self.stats.total_found += 1
                    
                    # Update status distribution
                    self.stats.status_distribution[result.status] = \
                        self.stats.status_distribution.get(result.status, 0) + 1
                    
                    # Update technology distribution
                    for tech in result.technologies:
                        self.stats.tech_distribution[tech] = \
                            self.stats.tech_distribution.get(tech, 0) + 1
                    
                    # Update CMS distribution
                    if result.cms:
                        self.stats.cms_distribution[result.cms] = \
                            self.stats.cms_distribution.get(result.cms, 0) + 1
                    
                    # Update WAF distribution
                    if result.waf:
                        self.stats.waf_distribution[result.waf] = \
                            self.stats.waf_distribution.get(result.waf, 0) + 1
                
                # Call progress callback
                if progress_callback:
                    progress_callback(
                        len(self.results) + sum(1 for f in future_to_host if not f.done()),
                        self.stats.total_found,
                        0  # Error count not tracked here
                    )
        
        # Sort results
        self.results.sort(key=lambda x: (x.status, x.url))
        
        self.stats.end_time = time.time()
        
        return self.results