from django.conf import settings

import ccp


def app(request):
    return {
        "ccp_version": ccp.__version__,
        "ccp_profile": settings.CCP_PROFILE,
        "ccp_multi_user": settings.CCP_MULTI_USER,
        "ccp_eos": ccp.config.EOS,
    }
