import sys, logging, os
sys.path.append(r'e:\Python Projects\DeekSeekBingFinder')
from utils import edge_driver_manager as edm
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

driver = os.path.abspath('msedgedriver.exe')
print('local before:', edm.get_local_driver_version(driver))
res = edm.ensure_latest_msedgedriver(driver)
print('ensure_latest_msedgedriver returned:', res)
# If tuple, unpack
if isinstance(res, tuple):
    path, installed_ver, latest_avail = res
    print('installed_path=', path)
    print('installed_version=', installed_ver)
    print('latest_available=', latest_avail)
else:
    print('installed_path=', res)
    print('installed_version=', edm.get_local_driver_version(res))

print('local after:', edm.get_local_driver_version(driver))
