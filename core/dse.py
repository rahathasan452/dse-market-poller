import urllib3
from bdshare.util.helper import _session

def patch_dse_ssl():
    """
    Disables SSL verification for bdshare to workaround DSE certificate issues.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _session.verify = False
