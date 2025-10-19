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


def is_driver_usable(driver_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """Return True if the driver exists and reports a parsable version.

    This is a stronger check than os.path.exists() because it attempts to
    invoke the binary and parse its --version output. Use this to avoid
    treating corrupt or incompatible driver files as usable.
    """
    log = logger or logging.getLogger(__name__)
    try:
        if not driver_path:
            return False
        abs_path = os.path.abspath(driver_path)
        if not os.path.exists(abs_path):
            return False
        ver = get_local_driver_version(abs_path, log)
        if ver:
            log.debug(f"Driver at {abs_path} appears usable (version {ver}).")
            return True
        log.debug(f"Driver at {abs_path} exists but did not report a version.")
        return False
    except Exception as e:
        log.debug(f"is_driver_usable check failed for {driver_path}: {e}")
        return False


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
        # Try to find explicit ZIP URLs on the page first (capture full URL and version)
        url_pattern = rf"https?://[^\"'<>]+/(\d+\.\d+\.\d+\.\d+)/edgedriver_{platform_tag}\.zip"
        url_matches = re.findall(url_pattern, html)
        if url_matches:
            # re.findall with this pattern returns the captured version groups; to find full URLs, run finditer
            found = {}
            for m in re.finditer(url_pattern, html):
                full = m.group(0)
                ver = m.group(1)
                found[ver] = full
            if found:
                # sort versions and prefer microsoft domain when possible
                versions = sorted(found.keys(), key=_version_tuple, reverse=True)
                best = versions[0]
                url = found[best]
                # If the chosen URL does not use microsoft.com, construct microsoft link and prefer it if reachable
                candidate_ms = _build_download_url(best, platform_tag, domain="microsoft")
                if candidate_ms != url and _url_exists(candidate_ms):
                    url = candidate_ms
                log.info(f"Developer portal suggests latest msedgedriver {best} for {platform_tag} at {url}")
                return best, url

        # If no explicit URLs found, try a more general approach: find dotted versions on the page
        # and probe the canonical download URLs for our platform.
        ver_candidates = sorted(set(re.findall(r"(\d+\.\d+\.\d+\.\d+)", html)), key=_version_tuple, reverse=True)
        if not ver_candidates:
            log.warning("Could not find any edgedriver version strings on developer portal.")
            return None

        log.debug(f"Found version candidates on portal: {ver_candidates[:5]}")
        for ver in ver_candidates:
            candidate = _build_download_url(ver, platform_tag, domain="microsoft")
            log.debug(f"Probing candidate URL: {candidate}")
            try:
                if _url_exists(candidate):
                    log.info(f"Developer portal (probe) latest msedgedriver {ver}: {candidate}")
                    return ver, candidate
            except Exception:
                # ignore and continue probing
                pass

        log.warning("No reachable edgedriver download URL discovered by probing candidate versions.")
        return None
    except Exception as e:
        log.warning(f"Fallback to developer portal failed: {e}")
        return None


def _fetch_latest_from_devportal_by_xpath(logger: Optional[logging.Logger] = None) -> Optional[tuple[str, str]]:
    """Parse the developer portal using provided absolute XPaths to get version and URL.

    Returns (version, zip_url) or None on failure. Requires lxml; otherwise returns None.
    """
    log = logger or logging.getLogger(__name__)
    # If lxml is not available, attempt a robust text-based fallback that looks
    # specifically for the Stable channel download link near anchor nodes.
    if lxml_html is None:
        log.info("lxml not available; attempting text-based Stable-channel link discovery")
        try:
            # Fetch raw HTML and attempt to find anchor tags linking to edgedriver zips
            with urllib.request.urlopen(DEVPORTAL_URL, timeout=20) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                html_text = resp.read().decode("utf-8", errors="ignore")

            # Determine platform tag to prefer platform-specific zips
            try:
                tag = _detect_platform_tag()
            except Exception:
                tag = None

            # Attempt focused block-based extraction using known class markers
            # This helps when multiple driver versions are present on the page.
            block_markers = [
                'block-web-driver__versions',
                'block-centered__media',
                'common-pager__pages',
                'block-web-driver__version'
            ]
            for marker in block_markers:
                for mpos in re.finditer(re.escape(marker), html_text):
                    pos = mpos.start()
                    # wide window to capture surrounding markup
                    wstart = max(0, pos - 2500)
                    wend = min(len(html_text), pos + 2500)
                    window = html_text[wstart:wend]
                    # try to extract exact version from this window
                    ver = _parse_version(window)
                    if ver:
                        # look for platform-specific anchor in the window
                        anchor_re_local = re.compile(r'<a[^>]+href=["\']([^"\']*edgedriver_[^"\']*\.zip)["\'][^>]*>', re.I | re.S)
                        anchors = [urljoin(DEVPORTAL_URL, mm.group(1)) for mm in anchor_re_local.finditer(window)]
                        chosen = None
                        if anchors:
                            # prefer win64 anchors
                            for a in anchors:
                                if tag and f'edgedriver_{tag}.zip' in a:
                                    chosen = a
                                    break
                            if not chosen:
                                chosen = anchors[0]
                        # If we found anchor matching tag and version, accept it
                        if chosen and _parse_version(chosen) == ver:
                            log.info(f"Developer portal (focused block) latest msedgedriver {ver}: {chosen}")
                            return ver, chosen
                        # If no anchor but we have version, try the canonical microsoft URL
                        candidate_ms = _build_download_url(ver, tag or 'win64', domain='microsoft')
                        if _url_exists(candidate_ms):
                            log.info(f"Developer portal (focused block) latest msedgedriver {ver}: {candidate_ms}")
                            return ver, candidate_ms
                        # otherwise continue scanning other markers

            # Find all anchors that point to edgedriver zips
            anchor_re = re.compile(r'<a[^>]+href=["\']([^"\']*edgedriver_[^"\']*\.zip)["\'][^>]*>(.*?)</a>', re.I | re.S)
            candidates = []
            for m in anchor_re.finditer(html_text):
                href = m.group(1)
                inner = re.sub(r'<[^>]+>', '', m.group(2) or '')
                # Normalize absolute URL
                href_abs = urljoin(DEVPORTAL_URL, href)
                # Grab nearby context (200 chars before/after) to find 'stable' hints
                start = max(0, m.start() - 200)
                end = min(len(html_text), m.end() + 200)
                context = html_text[start:end]
                candidates.append((href_abs, inner.strip(), context, m.start()))

            # First: explicitly scan for 'stable' occurrences and look for anchors nearby.
            stable_window_candidates = []
            for match in re.finditer(r"\bstable\b|stable channel", html_text, re.I):
                pos = match.start()
                # Use a wider window to capture surrounding markup for the stable block
                wstart = max(0, pos - 2000)
                wend = min(len(html_text), pos + 2000)
                window = html_text[wstart:wend]
                for m in anchor_re.finditer(window):
                    href = urljoin(DEVPORTAL_URL, m.group(1))
                    ver = _parse_version(href)
                    stable_window_candidates.append((ver, href, pos))

            pick = None
            # Prefer stable-window candidates (closest to a 'stable' marker) and prefer platform tag
            if stable_window_candidates:
                # filter by platform tag first
                by_ver = {}
                for ver, href, pos in stable_window_candidates:
                    if not ver:
                        continue
                    if tag and f"edgedriver_{tag}.zip" in href:
                        by_ver[ver] = href
                if not by_ver:
                    # fallback to any ver found in stable windows
                    for ver, href, pos in stable_window_candidates:
                        if ver:
                            by_ver[ver] = href
                if by_ver:
                    best = sorted(by_ver.keys(), key=_version_tuple, reverse=True)[0]
                    pick = (best, by_ver[best])

            # If none matched stable windows, fall back to previous 'nearby context' heuristic
            if not pick:
                # Prefer candidate where nearby context or inner text mentions 'stable'
                stable_candidates = []
                for href, inner, context, spos in candidates:
                    combined = (inner + ' ' + context).lower()
                    if 'stable' in combined or 'stable channel' in combined:
                        stable_candidates.append(href)

                # If we have stable candidates, pick the highest version by parsing dotted versions
                if stable_candidates:
                    by_ver = {}
                    for href in stable_candidates:
                        ver = _parse_version(href) or _parse_version(' '.join(stable_candidates))
                        if ver:
                            by_ver[ver] = href
                    if by_ver:
                        # choose highest
                        best = sorted(by_ver.keys(), key=_version_tuple, reverse=True)[0]
                        pick = (best, by_ver[best])
                    else:
                        # fallback: choose the first stable candidate and parse version from URL
                        href = stable_candidates[0]
                        ver = _parse_version(href)
                        if ver:
                            pick = (ver, href)

            # If none matched stable context but there are any candidates, prefer platform tag matches
            if not pick and candidates:
                by_ver = {}
                for href, inner, context, spos in candidates:
                    if tag and f"edgedriver_{tag}.zip" in href:
                        ver = _parse_version(href)
                        if ver:
                            by_ver[ver] = href
                if by_ver:
                    best = sorted(by_ver.keys(), key=_version_tuple, reverse=True)[0]
                    pick = (best, by_ver[best])

            if pick:
                log.info(f"Developer portal (text fallback) latest msedgedriver {pick[0]}: {pick[1]}")
                return pick
            log.info("Text-based Stable-channel discovery did not find a match; falling back to other methods")
        except Exception as e:
            log.warning(f"Text-based XPath fallback failed: {e}")
        return None
    # Try multiple XPaths in order. The first is the user-provided Stable-channel
    # anchor (span inside the a[3] node). The second is a previous fallback.
    xpath_candidates = [
        '//*[@id="main"]/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[2]/div/a[3]',
        '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[2]/div/a[3]',
        '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div/div[1]/div/div/div/div[1]',
        '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[1]/div/h3/div'
    ]
    # version text can live in nearby text nodes or inside a span within the same container
    version_xpaths = [
        # User-supplied: exact version text node
        '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[2]/text()',
        '//*[@id="main"]/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[2]/div/a[3]/span',
        '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div[1]/div/div/div/div[1]/div/div[2]/text()',
        '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[1]/div/h3/div'
    ]
    attempt = 0
    while attempt < DEFAULT_RETRIES:
        try:
            with urllib.request.urlopen(DEVPORTAL_URL, timeout=20) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                html_text = resp.read().decode("utf-8", errors="ignore")
            log.debug(f"Using XPath candidates -> links: {xpath_candidates}, versions: {version_xpaths}")
            tree = lxml_html.fromstring(html_text)
            href = None
            # Prefer locating the Stable-channel block first (user-provided XPaths).
            # If any block exists, search inside it for edgedriver ZIP anchors and prefer platform-specific links.
            try:
                block_xpaths = [
                    '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[1]/div',
                    '/html/body/div[1]/div/main/div/div[1]/section[3]/div[2]/div/div/div/div[2]/div/div/div/div/div[1]/div/div/div/div[1]/div/div[2]'
                ]
                for block_xpath in block_xpaths:
                    blocks = tree.xpath(block_xpath)
                    if blocks:
                        log.debug(f"Found block via XPath: {block_xpath} (count={len(blocks)})")
                        tag = None
                        try:
                            tag = _detect_platform_tag()
                        except Exception:
                            tag = None
                        for blk in blocks:
                            try:
                                anchors = blk.xpath('.//a[contains(@href, "edgedriver_") and contains(@href, ".zip")]')
                            except Exception:
                                anchors = []
                            if not anchors:
                                continue
                            chosen = None
                            for a in anchors:
                                try:
                                    a_href = a.get('href')
                                except Exception:
                                    a_href = None
                                if not a_href:
                                    continue
                                # Prefer win64 (x64) version
                                if tag and f"edgedriver_{tag}.zip" in a_href:
                                    chosen = a_href
                                    break
                                if chosen is None:
                                    chosen = a_href
                            if chosen:
                                href = urljoin(DEVPORTAL_URL, chosen)
                                ver = _parse_version(href) or _parse_version(chosen)
                                if ver and tag:
                                    candidate_ms = _build_download_url(ver, tag, domain='microsoft')
                                    if _url_exists(candidate_ms):
                                        href = candidate_ms
                                log.info(f"Developer portal (Block XPath) latest msedgedriver {ver}: {href}")
                                if ver and href:
                                    return ver, href
                                # otherwise continue to other XPath parsing
            except Exception as e:
                log.debug(f"Block XPath processing failed: {e}")
            # Try candidate XPaths in order
            for lx in xpath_candidates:
                try:
                    link_nodes = tree.xpath(lx)
                except Exception:
                    link_nodes = []
                log.debug(f"XPath '{lx}' link nodes count: {len(link_nodes)}")
                if link_nodes:
                    # If we selected a span node, find the closest ancestor <a>
                    node = link_nodes[0]
                    try:
                        # If node is an element and has get('href'), use it. Otherwise look for ancestor a
                        href = node.get('href') if hasattr(node, 'get') and node.get('href') else None
                    except Exception:
                        href = None
                    if not href:
                        # search upward for <a> ancestor
                        parent = node.getparent() if hasattr(node, 'getparent') else None
                        while parent is not None and getattr(parent, 'tag', '').lower() != 'a':
                            parent = parent.getparent() if hasattr(parent, 'getparent') else None
                        if parent is not None and getattr(parent, 'tag', '').lower() == 'a':
                            href = parent.get('href')
                    if href:
                        # Prefer this href only if it corresponds to the Stable channel.
                        # Check nearby text (node text + ancestor text) for the word 'stable'.
                        try:
                            # gather text from node and a few ancestors
                            texts = []
                            if hasattr(node, 'text') and node.text:
                                texts.append(node.text)
                            # include parent/ancestor textual context up to 3 levels
                            p = node.getparent() if hasattr(node, 'getparent') else None
                            levels = 0
                            while p is not None and levels < 3:
                                try:
                                    txt = ''.join(p.itertext()) if hasattr(p, 'itertext') else (p.text or '')
                                except Exception:
                                    txt = p.text or ''
                                if txt:
                                    texts.append(txt)
                                p = p.getparent() if hasattr(p, 'getparent') else None
                                levels += 1
                            combined_text = ' '.join(t.strip() for t in texts if t)
                        except Exception:
                            combined_text = ''

                        if 'stable' in combined_text.lower() or 'stable channel' in combined_text.lower():
                            # Validate platform-specific zip in href or try constructing candidate
                            tag = None
                            try:
                                tag = _detect_platform_tag()
                            except Exception:
                                tag = None

                            # If href already has correct platform, accept it
                            if tag and f"edgedriver_{tag}.zip" in href:
                                break
                            # Else try microsoft platform candidate for the parsed version
                            ver_from_href = _parse_version(href)
                            if ver_from_href and tag:
                                candidate_ms = _build_download_url(ver_from_href, tag, domain='microsoft')
                                if _url_exists(candidate_ms):
                                    href = candidate_ms
                                    break
                            # Accept the href even if platform check failed; higher-level
                            # code will try to switch platform if needed.
                            break
            log.debug(f"XPath href extracted: {href}")
            if href:
                href = urljoin(DEVPORTAL_URL, href)
            log.debug(f"XPath href extracted: {href}")
            # version text nodes may include extra words; attempt multiple xpaths
            version_nodes = []
            for vx in version_xpaths:
                try:
                    nodes = tree.xpath(vx)
                except Exception:
                    nodes = []
                if nodes:
                    version_nodes = nodes
                    log.debug(f"Using version xpath '{vx}' with {len(nodes)} nodes")
                    break
            log.debug(f"XPath version nodes count: {len(version_nodes)}")
            # Convert version nodes (which may be strings or elements) into text
            texts = []
            for v in version_nodes:
                try:
                    if isinstance(v, str):
                        t = v.strip()
                    else:
                        # lxml elements support text_content(); fallback to itertext
                        if hasattr(v, 'text_content'):
                            t = v.text_content().strip()
                        else:
                            t = ''.join(v.itertext()).strip() if hasattr(v, 'itertext') else (v.text or '')
                    if t:
                        texts.append(t)
                except Exception:
                    continue
            combined = " ".join(texts)
            preview = (combined[:200] + "...") if len(combined) > 200 else combined
            log.debug(f"XPath version text combined (truncated): '{preview}'")
            exact_version = _parse_version(combined)
            ver = exact_version or _parse_version(href or "")
            log.info(f"XPath parse results -> version: {ver}, url: {href}")
            # Construct the download URL using the extracted version
            if exact_version:
                stable_url = f"https://msedgedriver.microsoft.com/{exact_version}/edgedriver_win64.zip"
                # Check if the URL exists
                try:
                    with urllib.request.urlopen(stable_url, timeout=10) as resp:
                        if resp.status == 200:
                            log.info(f"Stable msedgedriver found: {exact_version} at {stable_url}")
                            return exact_version, stable_url
                        else:
                            log.warning(f"Stable msedgedriver URL returned status {resp.status}: {stable_url}")
                except Exception as e:
                    log.warning(f"Stable msedgedriver URL not accessible: {stable_url} ({e})")
            log.debug("Could not construct or access stable msedgedriver URL")
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

    if latest and local:
        if _version_tuple(local) >= _version_tuple(latest):
            log.info(f"Local msedgedriver is up to date ({local}). Latest available: {latest} -> {url}")
            return abs_path, local, latest
        else:
            log.info(f"Local msedgedriver version {local} is older than latest available {latest}. Update will be performed.")

    try:
        if not url:
            got = _fetch_latest_from_devportal(tag, log)
            if not got:
                log.warning("Could not determine latest msedgedriver version; proceeding with existing driver if available.")
                return abs_path, local, latest
            latest, url = got
            log.info(f"Latest Edge WebDriver URL: {url}")

        log.info(f"Starting download and update of Edge WebDriver {latest} for {tag} from: {url}")
        data = _download(url)
        out_path = _extract_driver(data, dest_dir)
        # Verify version after install
        new_ver = get_local_driver_version(out_path, log)
        if new_ver:
            log.info(f"Update complete: Installed msedgedriver {new_ver} at {out_path}")
        else:
            log.info(f"Update complete: Installed msedgedriver at {out_path}")
        return out_path, new_ver, latest
    except Exception as e:
        log.warning(f"Failed to update msedgedriver automatically: {e}")
        return abs_path, local, latest
