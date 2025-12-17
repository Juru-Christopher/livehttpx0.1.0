"""
Input/output parsing for livehttpx
"""

import json
import csv
from typing import List, Dict, Any
from .models import ScanResult, ScanStats
from .utils import format_time
import datetime


class OutputParser:
    """Handle output parsing and formatting"""
    
    @staticmethod
    def save_to_txt(results: List[ScanResult], filename: str, 
                   show_details: bool = False, stats: ScanStats = None):
        """Save results in text format"""
        with open(filename, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# livehttpx Scan Results\n")
            f.write(f"# Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if stats:
                f.write(f"# Total checked: {stats.total_checked}\n")
                f.write(f"# Live hosts: {stats.total_found}\n")
                f.write(f"# Success rate: {stats.success_rate:.1f}%\n")
                f.write(f"# Scan time: {format_time(stats.elapsed_time)}\n")
            f.write("#" * 50 + "\n\n")
            
            # Simple format - just URLs
            for host in results:
                f.write(f"{host.url}\n")
            
            # Add details if requested
            if show_details:
                f.write("\n# Detailed information:\n")
                f.write("#" * 50 + "\n")
                for host in results:
                    details = []
                    details.append(f"URL: {host.url}")
                    details.append(f"Status: {host.status}")
                    if host.title:
                        details.append(f"Title: {host.title}")
                    if host.ip_address:
                        details.append(f"IP: {host.ip_address}")
                    if host.server:
                        details.append(f"Server: {host.server}")
                    if host.content_length > 0:
                        details.append(f"Size: {host.content_length}")
                    if host.response_time > 0:
                        details.append(f"Time: {host.response_time:.3f}s")
                    if host.technologies:
                        details.append(f"Tech: {', '.join(host.technologies)}")
                    if host.cms:
                        details.append(f"CMS: {host.cms}")
                    if host.waf:
                        details.append(f"WAF: {host.waf}")
                    if host.cdn:
                        details.append(f"CDN: {host.cdn}")
                    if host.has_form:
                        details.append("Has Forms: Yes")
                    if host.has_login:
                        details.append("Has Login: Yes")
                    
                    f.write(" | ".join(details) + "\n")
    
    @staticmethod
    def save_to_json(results: List[ScanResult], filename: str, 
                    config: Dict[str, Any] = None, stats: ScanStats = None):
        """Save results in JSON format"""
        output = {
            'metadata': {
                'tool': 'livehttpx',
                'version': '0.1.0',
                'scan_time': datetime.datetime.now().isoformat(),
                'config': config or {},
            },
            'results': [host.to_dict() for host in results]
        }
        
        if stats:
            output['metadata'].update({
                'stats': {
                    'total_checked': stats.total_checked,
                    'total_found': stats.total_found,
                    'success_rate': stats.success_rate,
                    'elapsed_time': stats.elapsed_time,
                    'status_distribution': stats.status_distribution,
                    'tech_distribution': stats.tech_distribution,
                    'cms_distribution': stats.cms_distribution,
                    'waf_distribution': stats.waf_distribution,
                }
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    
    @staticmethod
    def save_to_csv(results: List[ScanResult], filename: str, 
                   show_details: bool = True):
        """Save results in CSV format"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if show_details:
                # Determine which fields to include
                fields = ['url', 'status', 'title', 'content_length', 'server', 
                         'ip_address', 'response_time']
                
                # Add optional fields if they exist in any result
                optional_fields = ['technologies', 'cms', 'waf', 'cdn', 
                                  'has_form', 'has_login']
                for field in optional_fields:
                    if any(getattr(r, field) for r in results):
                        fields.append(field)
                
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                
                for host in results:
                    row = {field: getattr(host, field) for field in fields}
                    # Handle list fields
                    if 'technologies' in row and isinstance(row['technologies'], list):
                        row['technologies'] = ';'.join(row['technologies'])
                    writer.writerow(row)
            else:
                # Just URLs
                for host in results:
                    f.write(f"{host.url}\n")
    
    @staticmethod
    def save_to_markdown(results: List[ScanResult], filename: str, 
                        stats: ScanStats = None):
        """Save results in Markdown format"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# livehttpx Scan Report\n\n")
            f.write(f"**Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if stats:
                f.write("## Summary\n\n")
                f.write(f"- **Total Checked**: {stats.total_checked}\n")
                f.write(f"- **Live Hosts**: {stats.total_found}\n")
                f.write(f"- **Success Rate**: {stats.success_rate:.1f}%\n")
                f.write(f"- **Scan Time**: {format_time(stats.elapsed_time)}\n\n")
            
            f.write("## Live Hosts\n\n")
            f.write("| URL | Status | Title | Size | Time | IP |\n")
            f.write("|-----|--------|-------|------|------|----|\n")
            
            for host in results:
                title = host.title[:50] if host.title else ""
                size = f"{host.content_length:,}" if host.content_length else "0"
                time_str = f"{host.response_time:.3f}s" if host.response_time else "N/A"
                ip = host.ip_address if host.ip_address else "N/A"
                
                f.write(f"| `{host.url}` | {host.status} | {title} | {size} | {time_str} | {ip} |\n")
            
            # Add statistics tables if available
            if stats and stats.status_distribution:
                f.write("\n## Status Code Distribution\n\n")
                f.write("| Status | Count |\n")
                f.write("|--------|-------|\n")
                for status, count in sorted(stats.status_distribution.items()):
                    f.write(f"| {status} | {count} |\n")