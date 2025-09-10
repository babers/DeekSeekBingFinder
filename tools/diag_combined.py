import sys, logging
sys.path.append(r'e:\Python Projects\DeekSeekBingFinder')
from utils import edge_driver_manager as edm
logging.basicConfig(level=logging.DEBUG)
print('combined->', edm.get_latest_download_url(edm._detect_platform_tag()))
