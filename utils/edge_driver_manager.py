"""Edge WebDriver manager: ensure latest msedgedriver is present on Windows.

Uses Microsoft's developer portal to resolve the latest version and builds the canonical
download URL as https://msedgedriver.microsoft.com/{version}/edgedriver_{platform}.zip
with a legacy fallback to azureedge.net if needed.

No third-party dependencies; uses urllib and zipfile.
"""

from __future__ import annotations

import io
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
import time
from typing import Optional
from urllib.parse import urljoin

try:
    from lxml import html as lxml_html  # type: ignore
except Exception:  # lxml is optional; regex fallback will be used if missing
    lxml_html = None


DEVPORTAL_URL = (
    "https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver?form=MA13LH"
)

# Retry/backoff defaults
DEFAULT_RETRIES = 3
BACKOFF_FACTOR = 2  # exponential factor
INITIAL_BACKOFF = 1  # in seconds


def _parse_version(text: str) -> Optional[str]:
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
    return match.group(1) if match else None


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(p) for p in v.split("."))
    except Exception:
        return tuple()


def get_local_driver_version(driver_path: str, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Return local msedgedriver version by invoking --version; None if missing/unknown."""
    log = logger or logging.getLogger(__name__)
    try:
        if not driver_path:
            return None
        abs_path = os.path.abspath(driver_path)
        if not os.path.exists(abs_path):
            return None
        result = subprocess.run([abs_path, "--version"], capture_output=True, text=True, timeout=10)
        out = (result.stdout or result.stderr or "").strip()
        ver = _parse_version(out)
        if ver:
            log.debug(f"Local msedgedriver version detected: {ver}")
        else:
            log.debug(f"Unable to parse msedgedriver version from: {out}")
        return ver
    except Exception as e:
        log.debug(f"Failed to get local msedgedriver version: {e}")
        return None


# Removed deprecated/invalid LATEST_STABLE endpoints; we now rely solely on the
# official developer portal content to infer the latest version and build the URL.


def _fetch_latest_from_devportal(platform_tag: str, logger: Optional[logging.Logger] = None) -> Optional[tuple[str, str]]:
    """Fallback: parse the developer portal for the highest version and its zip URL.

    Returns (version, zip_url) or None if not found.
    """
    log = logger or logging.getLogger(__name__)
    try:
        with urllib.request.urlopen(DEVPORTAL_URL, timeout=20) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            html = resp.read().decode("utf-8", errors="ignore")
        # Find all msedgedriver links (both domains) with version and platform zip
        pattern = rf"https://msedgedriver\\.(?:microsoft|azureedge)\\.com/(\\d+\\.\\d+\\.\\d+\\.\\d+)/edgedriver_{platform_tag}\\.zip"
        results = re.findall(pattern, html)
        if not results:
            log.warning("Could not find any edgedriver download links on developer portal.")
            return None
        # Deduplicate and pick the highest version
        versions = sorted(set(results), key=_version_tuple, reverse=True)
        best = versions[0]
        # Prefer microsoft.com domain for the final URL
        url = _build_download_url(best, platform_tag, domain="microsoft")
        log.info(f"Developer portal suggests latest msedgedriver {best} for {platform_tag} at {url}")
        return best, url
    except Exception as e:
        log.warning(f"Fallback to developer portal failed: {e}")
        return None


def _fetch_latest_from_devportal_by_xpath(logger: Optional[logging.Logger] = None) -> Optional[tuple[str, str]]:
    """Parse the developer portal using provided absolute XPaths to get version and URL.

    Returns (version, zip_url) or None on failure. Requires lxml; otherwise returns None.
    """
    log = logger or logging.getLogger(__name__)
    if lxml_html is None:
        log.info("lxml not available; skipping XPath-based parsing of developer portal")
        return None
    link_xpath = (
        "/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/"
        "div/div/div/div[1]/div/div/div/div[1]/div/div[2]/div/a[3]"
    )
    version_xpath = (
        "/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/"
        "div/div/div/div[1]/div/div/div/div[1]/div/div[2]/text()"
    )
    attempt = 0
    while attempt < DEFAULT_RETRIES:
        try:
            with urllib.request.urlopen(DEVPORTAL_URL, timeout=20) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                html_text = resp.read().decode("utf-8", errors="ignore")
            log.debug(f"Using XPaths -> link: '{link_xpath}', version: '{version_xpath}'")
            tree = lxml_html.fromstring(html_text)
            link_nodes = tree.xpath(link_xpath)
            log.debug(f"XPath link nodes count: {len(link_nodes)}")
            href = link_nodes[0].get("href") if link_nodes else None
            if href:
                href = urljoin(DEVPORTAL_URL, href)
            log.debug(f"XPath href extracted: {href}")
            # version text nodes may include extra words; extract dotted version
            version_nodes = tree.xpath(version_xpath)
            log.debug(f"XPath version nodes count: {len(version_nodes)}")
            combined = " ".join(v.strip() for v in version_nodes if isinstance(v, str))
            preview = (combined[:200] + "...") if len(combined) > 200 else combined
            log.debug(f"XPath version text combined (truncated): '{preview}'")
            ver = _parse_version(combined) or _parse_version(href or "")
            log.info(f"XPath parse results -> version: {ver}, url: {href}")
            if href and ver:
                log.info(f"Developer portal (XPath) latest msedgedriver {ver}: {href}")
                return ver, href
            log.debug("XPath parse did not yield both version and href")
            return None
        except Exception as e:
            attempt += 1
            log.warning(f"XPath parsing of developer portal failed (attempt {attempt}/{DEFAULT_RETRIES}): {e}")
            if attempt >= DEFAULT_RETRIES:
                return None
            backoff = INITIAL_BACKOFF * (BACKOFF_FACTOR ** (attempt - 1))
            time.sleep(backoff)


def _detect_platform_tag() -> str:
    """Return edgedriver platform tag, e.g., 'win64' or 'win32'. Defaults to win64 on 64-bit Windows."""
    if platform.system().lower().startswith("win"):
        arch = platform.machine().lower()
        # Use win64 for AMD64/x86_64/arm64; Edge ships ARM64 too, but win64 works for most AMD64 systems
        if "64" in arch or arch in ("amd64", "x86_64", "arm64", "aarch64"):
            return "win64"
        return "win32"
    raise OSError("Edge WebDriver manager currently supports Windows only.")


def _build_download_url(version: str, platform_tag: str, domain: str = "microsoft") -> str:
    base = "https://msedgedriver.microsoft.com" if domain == "microsoft" else "https://msedgedriver.azureedge.net"
    return f"{base}/{version}/edgedriver_{platform_tag}.zip"


def _url_exists(url: str, timeout: int = 8) -> bool:
    """Return True if a HEAD request to url returns HTTP 200.

    Uses urllib.request.Request with method='HEAD' when available; falls back to
    attempting a short GET and checking status.
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except TypeError:
        # Some older Python builds may not support Request(method=...)
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False
    except Exception:
        return False


def get_latest_download_url(platform_tag: Optional[str] = None, logger: Optional[logging.Logger] = None) -> Optional[tuple[str, str]]:
    """Return (version, url) for the latest driver by parsing the developer portal."""
    log = logger or logging.getLogger(__name__)
    try:
        tag = platform_tag or _detect_platform_tag()
    except Exception as e:
        log.warning(f"Platform detection failed: {e}")
        return None
    # First try strict XPath-based extraction. Accept it only if the returned URL
    # matches the requested platform (e.g., edgedriver_win64.zip). Otherwise
    # ignore the XPath result and fall back to the regex extraction which is
    # filtered by platform_tag.
    via_xpath = _fetch_latest_from_devportal_by_xpath(log)
    if via_xpath:
        ver, url = via_xpath
        # If the XPath-extracted URL already matches the platform, accept it.
        if tag and f"edgedriver_{tag}.zip" in (url or ""):
            log.info(f"Latest WebDriver URL (XPath): {url}")
            return ver, url
        # Otherwise, try to construct a platform-specific URL for the same
        # version (e.g., switch mac64 -> win64) and verify it exists before
        # accepting it. This handles the portal referencing multiple zips.
        candidate = _build_download_url(ver, tag, domain="microsoft")
        if _url_exists(candidate):
            log.info(f"Using XPath-detected version {ver} but switching to platform URL: {candidate}")
            return ver, candidate
        log.info(f"XPath-derived URL does not match platform '{tag}' and candidate {candidate} not reachable: {url} -- using regex fallback")
    # Then try regex fallback filtered by platform tag
    via_regex = _fetch_latest_from_devportal(tag, log)
    if via_regex:
        ver, url = via_regex
        log.info(f"Latest WebDriver URL (regex): {url}")
        return ver, url
    return None


def _download(url: str, timeout: int = 60) -> bytes:
    # Retry with exponential backoff for transient network failures
    attempt = 0
    while attempt < DEFAULT_RETRIES:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download: HTTP {resp.status}")
                return resp.read()
        except Exception:
            attempt += 1
            if attempt >= DEFAULT_RETRIES:
                raise
            backoff = INITIAL_BACKOFF * (BACKOFF_FACTOR ** (attempt - 1))
            time.sleep(backoff)


def _extract_driver(zip_bytes: bytes, dest_dir: str) -> str:
    """Extract msedgedriver.exe from zip bytes into dest_dir. Returns path to the driver."""
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Find msedgedriver.exe entry
        member = None
        for name in zf.namelist():
            if name.lower().endswith("msedgedriver.exe") and not name.endswith("/"):
                member = name
                break
        if not member:
            raise RuntimeError("msedgedriver.exe not found in archive")

        tmp_dir = tempfile.mkdtemp(prefix="edgedriver_")
        try:
            zf.extract(member, tmp_dir)
            src_path = os.path.join(tmp_dir, member)
            dest_path = os.path.join(dest_dir, "msedgedriver.exe")
            # Move into place (replace existing)
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except PermissionError:
                    # try rename old
                    os.rename(dest_path, dest_path + ".old")
            shutil.move(src_path, dest_path)
            return dest_path
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def ensure_msedgedriver_from_url(url: str, driver_path: str) -> str:
    """Download and install Edge WebDriver from a specific zip URL.

    Returns the absolute path to the installed driver. On failure, returns input path.
    """
    log = logging.getLogger(__name__)
    abs_path = os.path.abspath(driver_path or "msedgedriver.exe")
    dest_dir = os.path.dirname(abs_path) or os.getcwd()
    try:
        log.info(f"Downloading Edge WebDriver from provided URL: {url}")
        data = _download(url)
        out_path = _extract_driver(data, dest_dir)
        new_ver = get_local_driver_version(out_path, log)
        if new_ver:
            log.info(f"Installed msedgedriver {new_ver} at {out_path}")
        else:
            log.info(f"Installed msedgedriver at {out_path}")
        return out_path
    except Exception as e:
        log.warning(f"Failed to install msedgedriver from URL: {e}")
        return abs_path


def ensure_msedgedriver_version(version: str, driver_path: str) -> str:
    """Download and install the specified Edge WebDriver version.

    Builds https://msedgedriver.microsoft.com/{version}/edgedriver_{platform}.zip,
    downloads it, and replaces the local msedgedriver.exe.
    Returns the absolute path to the installed driver.
    """
    log = logging.getLogger(__name__)
    abs_path = os.path.abspath(driver_path or "msedgedriver.exe")
    dest_dir = os.path.dirname(abs_path) or os.getcwd()
    try:
        tag = _detect_platform_tag()
    except Exception as e:
        log.warning(f"Platform detection failed: {e}")
        return abs_path
    url = _build_download_url(version, tag, domain="microsoft")
    log.info(f"Downloading specified Edge WebDriver {version} for {tag} from: {url}")
    try:
        data = _download(url)
        out_path = _extract_driver(data, dest_dir)
        new_ver = get_local_driver_version(out_path, log)
        if new_ver:
            log.info(f"Installed msedgedriver {new_ver} at {out_path}")
        else:
            log.info(f"Installed msedgedriver at {out_path}")
        return out_path
    except Exception as e:
        log.warning(f"Failed to install specified msedgedriver {version}: {e}")
        return abs_path


def ensure_latest_msedgedriver(driver_path: str) -> tuple[str, Optional[str], Optional[str]]:
    """Ensure the latest Edge WebDriver is present at driver_path.

    Returns the absolute path to the driver (existing or newly downloaded).
    On failure to check or download, returns the input path (absolute) without raising.
    """
    log = logging.getLogger(__name__)
    abs_path = os.path.abspath(driver_path or "msedgedriver.exe")
    dest_dir = os.path.dirname(abs_path) or os.getcwd()

    # Determine platform tag once
    try:
        tag = _detect_platform_tag()
    except Exception as e:
        log.warning(f"Platform detection failed: {e}")
        return abs_path

    # Resolve latest version and canonical URL from the developer portal
    latest_info = get_latest_download_url(tag, log)
    latest = None
    url = None
    if latest_info:
        latest, url = latest_info
        log.info(f"Latest Edge WebDriver URL: {url}")

    local = get_local_driver_version(abs_path, log)

    if latest and local and _version_tuple(local) >= _version_tuple(latest):
        log.info(f"Local msedgedriver is up to date ({local}). Latest available: {latest} -> {url}")
        return abs_path, local, latest

    try:
        if not url:
            got = _fetch_latest_from_devportal(tag, log)
            if not got:
                log.warning("Could not determine latest msedgedriver version; proceeding with existing driver if available.")
                return abs_path, local, latest
            latest, url = got
            log.info(f"Latest Edge WebDriver URL: {url}")

        log.info(f"Downloading Edge WebDriver {latest} for {tag} from: {url}")
        data = _download(url)
        out_path = _extract_driver(data, dest_dir)
        # Verify version after install
        new_ver = get_local_driver_version(out_path, log)
        if new_ver:
            log.info(f"Installed msedgedriver {new_ver} at {out_path}")
        else:
            log.info(f"Installed msedgedriver at {out_path}")
        return out_path, new_ver, latest
    except Exception as e:
        log.warning(f"Failed to update msedgedriver automatically: {e}")
        return abs_path, local, latest
