"""
Custom exceptions for livehttpx
"""


class LivehttpxError(Exception):
    """Base exception for livehttpx"""
    pass


class ConfigError(LivehttpxError):
    """Configuration error"""
    pass


class InputError(LivehttpxError):
    """Input file/parameter error"""
    pass


class OutputError(LivehttpxError):
    """Output file error"""
    pass


class NetworkError(LivehttpxError):
    """Network-related error"""
    pass


class RateLimitError(NetworkError):
    """Rate limit exceeded"""
    pass


class TimeoutError(NetworkError):
    """Request timeout"""
    pass


class SSLError(NetworkError):
    """SSL certificate error"""
    pass