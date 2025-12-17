"""
Display and progress handling for livehttpx
"""

import sys
import time
import threading
from typing import List, Optional, Dict
from .models import TerminalInfo, ScanResult, ScanStats
from .utils import Color, format_size, format_time


class ProgressDisplay:
    """Advanced progress display with multiple styles"""
    
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    BAR_CHARS = [' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']
    
    def __init__(self, total: int, show_progress: bool = True, style: str = "bar", 
                 no_color: bool = False):
        self.total = total
        self.show_progress = show_progress
        self.style = style
        self.no_color = no_color
        self.checked = 0
        self.found = 0
        self.errors = 0
        self.start_time = time.time()
        self.last_update = 0
        self.spinner_idx = 0
        self.lock = threading.Lock()
        
    def update(self, checked: int, found: int, errors: int = 0):
        """Update progress counters"""
        with self.lock:
            self.checked = checked
            self.found = found
            self.errors = errors
            
            if self.show_progress and time.time() - self.last_update > 0.1:
                self._render_progress()
                self.last_update = time.time()
    
    def _render_progress(self):
        """Render progress based on selected style"""
        elapsed = time.time() - self.start_time
        percent = (self.checked / self.total * 100) if self.total > 0 else 0
        
        if self.style == "bar":
            self._render_progress_bar(percent, elapsed)
        elif self.style == "spinner":
            self._render_spinner(percent, elapsed)
        elif self.style == "detailed":
            self._render_detailed(percent, elapsed)
        else:  # simple
            self._render_simple(percent, elapsed)
    
    def _render_progress_bar(self, percent: float, elapsed: float):
        """Render progress bar"""
        bar_width = 30
        filled = int(bar_width * percent / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        
        # Estimate time remaining
        if percent > 0:
            remaining = (elapsed / percent) * (100 - percent)
            eta = f"ETA: {format_time(remaining)}"
        else:
            eta = "ETA: --:--"
        
        color = Color.CYAN if not self.no_color else ""
        reset = Color.RESET if not self.no_color else ""
        green = Color.GREEN if not self.no_color else ""
        red = Color.RED if not self.no_color else ""
        
        sys.stdout.write(f"\r\033[K{color}[{bar}] {percent:.1f}% | "
                        f"Checked: {self.checked}/{self.total} | "
                        f"Found: {green}{self.found}{reset} | "
                        f"Errors: {red}{self.errors}{reset} | "
                        f"Time: {format_time(elapsed)} | {eta}")
        sys.stdout.flush()
    
    def _render_spinner(self, percent: float, elapsed: float):
        """Render spinner progress"""
        spinner = self.SPINNER_CHARS[self.spinner_idx]
        self.spinner_idx = (self.spinner_idx + 1) % len(self.SPINNER_CHARS)
        
        color = Color.CYAN if not self.no_color else ""
        reset = Color.RESET if not self.no_color else ""
        green = Color.GREEN if not self.no_color else ""
        
        sys.stdout.write(f"\r\033[K{color}{spinner}{reset} "
                        f"Scanning... {self.checked}/{self.total} "
                        f"({percent:.1f}%) | "
                        f"Found: {green}{self.found}{reset} | "
                        f"Time: {format_time(elapsed)}")
        sys.stdout.flush()
    
    def _render_detailed(self, percent: float, elapsed: float):
        """Render detailed progress"""
        color = Color.CYAN if not self.no_color else ""
        reset = Color.RESET if not self.no_color else ""
        green = Color.GREEN if not self.no_color else ""
        yellow = Color.YELLOW if not self.no_color else ""
        
        # Calculate rates
        if elapsed > 0:
            rate = self.checked / elapsed
            found_rate = self.found / elapsed
        else:
            rate = found_rate = 0
        
        sys.stdout.write(f"\r\033[K{color}Progress:{reset} {self.checked}/{self.total} "
                        f"({percent:.1f}%) | "
                        f"{green}✓ {self.found}{reset} | "
                        f"{yellow}✗ {self.errors}{reset} | "
                        f"Rate: {rate:.1f}/s | "
                        f"Found rate: {found_rate:.1f}/s | "
                        f"Time: {format_time(elapsed)}")
        sys.stdout.flush()
    
    def _render_simple(self, percent: float, elapsed: float):
        """Render simple progress"""
        sys.stdout.write(f"\r\033[KProgress: {self.checked}/{self.total} ({percent:.1f}%) | "
                        f"Found: {self.found} | Time: {format_time(elapsed)}")
        sys.stdout.flush()
    
    def complete(self, stats: Optional[ScanStats] = None):
        """Display completion message"""
        if not self.show_progress:
            return
        
        sys.stdout.write("\r\033[K")  # Clear line
        
        elapsed = time.time() - self.start_time
        color = Color.GREEN if not self.no_color else ""
        reset = Color.RESET if not self.no_color else ""
        yellow = Color.YELLOW if not self.no_color else ""
        
        if self.found > 0:
            print(f"{color}[✓]{reset} Scan completed in {format_time(elapsed)}")
            print(f"{color}[✓]{reset} Found {self.found} live hosts out of {self.total} "
                  f"({(self.found/self.total*100):.1f}%)")
            if self.errors > 0:
                print(f"{yellow}[!]{reset} Encountered {self.errors} errors")
        else:
            print(f"{yellow}[!]{reset} Scan completed in {format_time(elapsed)}")
            print(f"{yellow}[!]{reset} No live hosts found")
        
        if stats:
            self._show_statistics(stats)
    
    def _show_statistics(self, stats: ScanStats):
        """Show scan statistics"""
        print(f"\n{Color.BOLD if not self.no_color else ''}Scan Statistics:{Color.RESET if not self.no_color else ''}")
        
        # Status code distribution
        if stats.status_distribution:
            print(f"{Color.CYAN if not self.no_color else ''}Status Code Distribution:{Color.RESET if not self.no_color else ''}")
            for status, count in sorted(stats.status_distribution.items()):
                color = self._get_status_color(status)
                print(f"  {color}HTTP {status}{Color.RESET if not self.no_color else ''}: {count}")
        
        # Technology distribution
        if stats.tech_distribution:
            print(f"\n{Color.CYAN if not self.no_color else ''}Technology Distribution:{Color.RESET if not self.no_color else ''}")
            for tech, count in sorted(stats.tech_distribution.items(), 
                                     key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {Color.CYAN if not self.no_color else ''}{tech}{Color.RESET if not self.no_color else ''}: {count}")
        
        # CMS distribution
        if stats.cms_distribution:
            print(f"\n{Color.CYAN if not self.no_color else ''}CMS Distribution:{Color.RESET if not self.no_color else ''}")
            for cms, count in sorted(stats.cms_distribution.items(), 
                                    key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {Color.MAGENTA if not self.no_color else ''}{cms}{Color.RESET if not self.no_color else ''}: {count}")
        
        # WAF distribution
        if stats.waf_distribution:
            print(f"\n{Color.CYAN if not self.no_color else ''}WAF Distribution:{Color.RESET if not self.no_color else ''}")
            for waf, count in sorted(stats.waf_distribution.items(), 
                                    key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {Color.YELLOW if not self.no_color else ''}{waf}{Color.RESET if not self.no_color else ''}: {count}")
    
    def _get_status_color(self, status: int) -> str:
        """Get color for status code"""
        if self.no_color:
            return ""
        
        if status < 300:
            return Color.GREEN
        elif status < 400:
            return Color.YELLOW
        elif status < 500:
            return Color.RED
        else:
            return Color.MAGENTA


class ResultDisplay:
    """Display scan results"""
    
    def __init__(self, terminal: TerminalInfo, no_color: bool = False, 
                 show_details: bool = False, max_title_length: int = 50):
        self.terminal = terminal
        self.no_color = no_color
        self.show_details = show_details
        self.max_title_length = max_title_length
    
    def display(self, results: List[ScanResult], stats: Optional[ScanStats] = None):
        """Display results"""
        if not results:
            color = Color.YELLOW if not self.no_color else ""
            reset = Color.RESET if not self.no_color else ""
            print(f"\n{color}[!]{reset} No live hosts found")
            return
        
        print(f"\n{Color.CYAN if not self.no_color else ''}{'=' * 60}{Color.RESET if not self.no_color else ''}")
        print(f"{Color.BOLD if not self.no_color else ''} LIVE HOSTS ({len(results)} found){Color.RESET if not self.no_color else ''}")
        print(f"{Color.CYAN if not self.no_color else ''}{'=' * 60}{Color.RESET if not self.no_color else ''}")
        
        if self.show_details:
            self._display_detailed(results)
        else:
            self._display_simple(results)
        
        print(f"{Color.CYAN if not self.no_color else ''}{'=' * 60}{Color.RESET if not self.no_color else ''}")
    
    def _display_simple(self, results: List[ScanResult]):
        """Display simple list of live URLs only"""
        for i, host in enumerate(results, 1):
            status_color = self._get_status_color(host.status)
            status_str = f"[{host.status}]"
            if not self.no_color:
                status_str = f"{status_color}{status_str}{Color.RESET}"
            
            print(f"{i:3d}. {status_str} {host.url}")
    
    def _display_detailed(self, results: List[ScanResult]):
        """Display detailed results"""
        # Determine column widths based on terminal width
        max_url_width = min(40, self.terminal.width - 60)
        max_title_width = min(self.max_title_length, self.terminal.width - 80)
        
        # Build header
        headers = ['No.', 'Status', 'URL', 'Title', 'Size', 'Time']
        if any(r.ip_address for r in results):
            headers.append('IP')
        if any(r.technologies for r in results):
            headers.append('Tech')
        if any(r.cms for r in results):
            headers.append('CMS')
        
        # Print header
        header_line = ' '.join(f"{h:<10}" if h != 'URL' else f"{h:<{max_url_width}}" for h in headers)
        print(header_line)
        print('-' * min(120, self.terminal.width))
        
        # Print rows
        for i, host in enumerate(results, 1):
            row_parts = []
            
            # Number
            row_parts.append(f"{i:<3}")
            
            # Status
            status_str = str(host.status)
            if not self.no_color:
                status_color = self._get_status_color(host.status)
                status_str = f"{status_color}{status_str}{Color.RESET}"
            row_parts.append(f"{status_str:<10}")
            
            # URL
            url = host.url
            if len(url) > max_url_width:
                url = url[:max_url_width - 3] + "..."
            row_parts.append(f"{url:<{max_url_width}}")
            
            # Title
            title = host.title[:max_title_width] if host.title else ""
            row_parts.append(f"{title:<{max_title_width}}")
            
            # Size
            size = format_size(host.content_length)
            row_parts.append(f"{size:<8}")
            
            # Response Time
            time_str = format_time(host.response_time)
            row_parts.append(f"{time_str:<6}")
            
            # IP (if available)
            if any(r.ip_address for r in results):
                ip = host.ip_address[:15] if host.ip_address else ""
                row_parts.append(f"{ip:<15}")
            
            # Technologies (if available)
            if any(r.technologies for r in results):
                tech_str = ", ".join(host.technologies[:2])[:13]
                if len(host.technologies) > 2:
                    tech_str += "..."
                row_parts.append(f"{tech_str:<15}")
            
            # CMS (if available)
            if any(r.cms for r in results):
                row_parts.append(f"{host.cms:<10}")
            
            print(' '.join(row_parts))
    
    def _get_status_color(self, status: int) -> str:
        """Get color for status code"""
        if self.no_color:
            return ""
        
        if status < 300:
            return Color.GREEN
        elif status < 400:
            return Color.YELLOW
        elif status < 500:
            return Color.RED
        else:
            return Color.MAGENTA