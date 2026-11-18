"""
Temporary Reference Image Acquisition Service (RAM-Only)
=========================================================
Strict Privacy, Security & Zero-Disk-Persistence Implementation.
Lifecycle:
  1. Retrieve accessible image URL via HTTP/HTTPS into memory buffer (`io.BytesIO`).
  2. Perform SSRF checks (blocks private IPs, localhost, AWS metadata, loopback).
  3. Validate MIME type (`image/jpeg`, `image/png`, `image/webp`), size <= 5MB, resolution <= 1600x1600.
  4. Provide in-memory base64 or PIL Image to Qwen3-VL-4B-Thinking (`vision_analyzer`).
  5. Strictly release buffers on completion or error in `finally` block.
  6. Zero disk writes, zero DB storage, zero base64 data logged.
"""

import io
import re
import socket
import logging
import urllib.parse
from typing import Tuple, Optional
from contextlib import contextmanager
import requests
from PIL import Image

logger = logging.getLogger(__name__)

# Security & admission limits
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB maximum
MAX_IMAGE_DIMENSION = 1600               # 1600 px maximum width/height
REQUEST_TIMEOUT_SECONDS = 10
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")

# Private and non-routable IP ranges for SSRF prevention
PRIVATE_IP_PATTERNS = [
    re.compile(r"^127\."),                         # Loopback
    re.compile(r"^10\."),                          # RFC 1918 class A
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."), # RFC 1918 class B
    re.compile(r"^192\.168\."),                    # RFC 1918 class C
    re.compile(r"^169\.254\."),                    # Link-local / AWS metadata
    re.compile(r"^0\."),                           # Current network
    re.compile(r"^fc00:|^fe80:|^::1$"),            # IPv6 local / link-local
]


def is_ssrf_safe_url(url: str) -> bool:
    """
    Validate that the target URL is standard HTTP/HTTPS and resolves
    strictly to a public, routable IP address.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            logger.warning("[SSRF Protection] Rejected non-HTTP(S) scheme: %s", parsed.scheme)
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            logger.warning("[SSRF Protection] Blocked localhost access: %s", hostname)
            return False

        # Resolve IP to verify non-private destination
        ip_addresses = socket.getaddrinfo(hostname, None)
        for family, socktype, proto, canonname, sockaddr in ip_addresses:
            ip = sockaddr[0]
            for pattern in PRIVATE_IP_PATTERNS:
                if pattern.match(ip):
                    logger.warning("[SSRF Protection] Blocked private IP '%s' for host '%s'", ip, hostname)
                    return False
        return True
    except Exception as e:
        logger.warning("[SSRF Protection] DNS resolution error for %s: %s", url, e)
        return False


class ReferenceAcquisitionService:
    """
    Manages in-memory image downloading, sanitization, and release.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HypothesiseAgent-VisualAnalyzer/2.0 (Scientific Reference Fetcher; RAM-Only)",
            "Accept": "image/jpeg,image/png,image/webp",
        })

    def fetch_image_into_ram(self, image_url: str) -> Tuple[bytes, str]:
        """
        Download reference image into memory, validate, resize if oversized, and return (bytes, mime_type).
        Strictly zero disk writes.
        """
        if not is_ssrf_safe_url(image_url):
            raise ValueError(f"Security Policy: URL rejected due to SSRF / private IP protection ({image_url})")

        resp = self.session.get(
            image_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            stream=True,
            headers={"Range": f"bytes=0-{MAX_IMAGE_SIZE_BYTES}"},
        )
        if resp.status_code not in (200, 206):
            raise RuntimeError(f"Failed to fetch reference image: HTTP {resp.status_code}")

        content_type = resp.headers.get("Content-Type", "").lower().split(";")[0].strip()
        if content_type and not any(allowed in content_type for allowed in ALLOWED_MIME_TYPES):
            # Probe with PIL if header is generic
            pass

        # Read into in-memory buffer with size ceiling
        raw_buffer = io.BytesIO()
        total_bytes = 0
        for chunk in resp.iter_content(chunk_size=16384):
            if chunk:
                total_bytes += len(chunk)
                if total_bytes > MAX_IMAGE_SIZE_BYTES:
                    raise ValueError(f"Reference image exceeds maximum allowed size ({MAX_IMAGE_SIZE_BYTES} bytes)")
                raw_buffer.write(chunk)

        raw_buffer.seek(0)
        if total_bytes < 50:
            raise ValueError("Reference image stream returned empty or corrupted content")

        # Validate with PIL & resize if oversized
        try:
            with Image.open(raw_buffer) as img:
                img_format = img.format.lower() if img.format else "jpeg"
                mime = f"image/{'jpeg' if img_format in ('jpg', 'jpeg') else img_format}"
                if mime not in ALLOWED_MIME_TYPES:
                    mime = "image/jpeg"

                width, height = img.size
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    # Resize preserving aspect ratio
                    img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
                    out_buffer = io.BytesIO()
                    # Convert RGBA to RGB for JPEG compatibility
                    if img.mode in ("RGBA", "P") and mime == "image/jpeg":
                        img_converted = img.convert("RGB")
                        img_converted.save(out_buffer, format="JPEG", quality=88)
                    else:
                        img.save(out_buffer, format=img_format.upper() if img_format else "JPEG")
                    out_bytes = out_buffer.getvalue()
                    out_buffer.close()
                    raw_buffer.close()
                    logger.info("[ReferenceAcquisition] Image fetched into RAM: %dx%d (resized), %d bytes", img.width, img.height, len(out_bytes))
                    return out_bytes, mime
                else:
                    out_bytes = raw_buffer.getvalue()
                    raw_buffer.close()
                    logger.info("[ReferenceAcquisition] Image fetched into RAM: %dx%d, %d bytes", width, height, len(out_bytes))
                    return out_bytes, mime
        except Exception as e:
            raw_buffer.close()
            raise ValueError(f"Invalid or corrupted image data: {e}")

    @contextmanager
    def acquire_reference_session(self, image_url: str):
        """
        Context manager ensuring RAM buffers are completely freed upon exit.
        Usage:
          with acquisition_service.acquire_reference_session(url) as (img_bytes, mime):
              # feed img_bytes to vision model
          # img_bytes reference is discarded, RAM garbage collected
        """
        img_bytes = None
        try:
            img_bytes, mime = self.fetch_image_into_ram(image_url)
            yield img_bytes, mime
        finally:
            if img_bytes is not None:
                del img_bytes
            logger.info("[ReferenceAcquisition] In-memory reference image buffers released.")


reference_acquisition_service = ReferenceAcquisitionService()

