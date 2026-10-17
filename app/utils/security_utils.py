import html
import ipaddress
import logging
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger("security")

# Cloud metadata addresses to strictly block
CLOUD_METADATA_IPS = {
    "169.254.169.254", # AWS / Azure / GCP instance metadata
    "fd00:ec2::254",   # AWS IPv6 metadata
}

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}

def validate_external_url(url: str, resolve_dns: bool = True) -> bool:
    """Validate that an outbound URL targets a safe, public external service.
    Defends against Server-Side Request Forgery (SSRF) by blocking:
    - Non-HTTP/HTTPS schemes (e.g. file://, gopher://, ftp://)
    - Localhost and loopback addresses (127.0.0.0/8, ::1)
    - Cloud provider metadata APIs (169.254.169.254)
    - Private RFC1918 networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local and carrier-grade NAT addresses
    """
    if not url or not isinstance(url, str):
        return False

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception:
        return False

    # 1. Scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False

    # 2. Blocklist of specific known dangerous hostnames
    if hostname in BLOCKED_HOSTNAMES:
        return False

    # 3. Direct IP address check
    try:
        direct_ip = ipaddress.ip_address(hostname)
        if direct_ip.is_loopback or direct_ip.is_private or direct_ip.is_link_local or direct_ip.is_reserved or direct_ip.is_multicast:
            return False
        if str(direct_ip) in CLOUD_METADATA_IPS:
            return False
    except ValueError:
        pass

    # 4. Resolve DNS to ensure hostname does not resolve to private/internal subnet
    if resolve_dns:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                resolved_ip = ipaddress.ip_address(ip_str)
                if resolved_ip.is_loopback or resolved_ip.is_private or resolved_ip.is_link_local or resolved_ip.is_reserved or resolved_ip.is_multicast:
                    return False
                if str(resolved_ip) in CLOUD_METADATA_IPS:
                    return False
        except (socket.gaierror, socket.herror, ValueError, Exception):
            # If domain cannot be resolved, reject request safely
            return False

    return True

def sanitize_html_input(text: Optional[str]) -> str:
    """Escape harmful HTML and JavaScript injection characters to prevent XSS attacks."""
    if not text:
        return ""
    return html.escape(str(text).strip(), quote=True)

def mask_ip_for_logs(ip: Optional[str]) -> str:
    """Mask IPv4 and IPv6 addresses for privacy-compliant security audit logs."""
    if not ip or ip in ("unknown", "127.0.0.1", "localhost", "testclient"):
        return ip or "unknown"
    
    clean_ip = ip.strip()
    if ":" in clean_ip:
        # IPv6
        parts = clean_ip.split(":")
        return ":".join(parts[:2]) + ":****:****"
    elif "." in clean_ip:
        # IPv4
        parts = clean_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    return clean_ip

def log_security_event(event_type: str, detail: str, client_ip: str = "unknown"):
    """Output structured security telemetry event."""
    timestamp = datetime.now(timezone.utc).isoformat()
    masked_ip = mask_ip_for_logs(client_ip)
    message = f"[SECURITY EVENT] [{timestamp}] [TYPE: {event_type}] [IP: {masked_ip}] {detail}"
    print(message)
    logger.warning(message)
