
from core.nexus_framework.plugin_SDK import _AccountsSDKFacade
def test():
    sdk = _AccountsSDKFacade()
    return sdk.get_token(3)
