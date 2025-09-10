import logging
import sys
sys.path.append(r'e:\Python Projects\DeekSeekBingFinder')
from utils import edge_driver_manager as edm

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
log = logging.getLogger('diag')

def show_regex(html, platform_tag='win64'):
    import re
    pattern = rf"https://msedgedriver\.(?:microsoft|azureedge)\.com/(\d+\.\d+\.\d+\.\d+)/edgedriver_{platform_tag}\.zip"
    results = re.findall(pattern, html)
    print('regex matches count:', len(results))
    if results:
        versions = sorted(set(results), key=edm._version_tuple, reverse=True)
        print('regex highest:', versions[0])
        print('sample urls:')
        for v in versions[:8]:
            print('  ', edm._build_download_url(v, platform_tag))


def main():
    tag = edm._detect_platform_tag()
    print('platform_tag=', tag)
    # Try XPath-based
    try:
        xpath = edm._fetch_latest_from_devportal_by_xpath()
        print('xpath result =', xpath)
    except Exception as e:
        print('xpath error', e)
    # Try regex/fallback by fetching page directly
    import urllib.request
    url = edm.DEVPORTAL_URL
    print('fetching', url)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print('fetch error', e)
        return
    # show some snippet
    print('\n===== page snippet =====')
    print(html[:2000])
    print('\n===== end snippet =====')
    show_regex(html, tag)

if __name__ == '__main__':
    main()
