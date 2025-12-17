"""
Data models for livehttpx
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import json
from datetime import datetime


@dataclass
class TerminalInfo:
    """Container for terminal display information"""
    width: int = 80
    height: int = 24
    supports_color: bool = True
    supports_unicode: bool = True


@dataclass
class ScanResult:
    """Data class for scan results"""
    url: str
    host: str
    status: int
    scheme: str
    title: str = ""
    content_length: int = 0
    server: str = ""
    ip_address: str = ""
    response_time: float = 0.0
    technologies: List[str] = field(default_factory=list)
    redirect_chain: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    has_form: bool = False
    has_login: bool = False
    is_wordpress: bool = False
    cms: str = ""
    waf: str = ""
    cdn: str = ""
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class ScanConfig:
    """Scan configuration"""
    timeout: int = 5
    max_workers: int = 50
    match_codes: List[int] = field(default_factory=lambda: [200, 201, 202, 204, 301, 302, 307, 308, 401, 403])
    verify_ssl: bool = True
    rate_limit: Optional[int] = None
    retries: int = 1
    follow_redirects: bool = True
    tech_detection: bool = False
    detect_waf: bool = False
    detect_cms: bool = False
    detect_cdn: bool = False
    extract_headers: bool = False
    extract_cookies: bool = False
    find_forms: bool = False
    find_logins: bool = False
    random_user_agent: bool = True
    custom_user_agent: Optional[str] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    exclude_codes: List[int] = field(default_factory=lambda: [])
    include_codes: List[int] = field(default_factory=lambda: [])
    only_https: bool = False
    only_http: bool = False
    show_title: bool = True
    show_size: bool = True
    show_ip: bool = True
    show_time: bool = True
    show_tech: bool = True


@dataclass
class ScanStats:
    """Scan statistics"""
    total_checked: int = 0
    total_found: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    status_distribution: Dict[int, int] = field(default_factory=dict)
    tech_distribution: Dict[str, int] = field(default_factory=dict)
    cms_distribution: Dict[str, int] = field(default_factory=dict)
    waf_distribution: Dict[str, int] = field(default_factory=dict)
    
    @property
    def elapsed_time(self):
        """Get elapsed time"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def success_rate(self):
        """Get success rate percentage"""
        if self.total_checked == 0:
            return 0.0
        return (self.total_found / self.total_checked) * 100