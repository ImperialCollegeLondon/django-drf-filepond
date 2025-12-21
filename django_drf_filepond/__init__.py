import sys
import warnings

from django_drf_filepond.deprecation import DjangoDrfFilepondDeprecationWarning

# This setting is remaining in place to support older versions of Python/Django
# however it is deprecated and removed in Django 4.1 where the setting
# is detected automatically.
default_app_config = 'django_drf_filepond.apps.DjangoDrfFilepondConfig'

# Trigger display of deprecation warning if running with py27, py35, py36, py37
if ((sys.version_info[:2] == (2, 7)) or
    (sys.version_info[:2] == (3, 5)) or
    (sys.version_info[:2] == (3, 6)) or
    (sys.version_info[:2] == (3, 7))):
    warnings.warn(
        "Python versions 2.7, 3.5, 3.6 and 3.7 will no longer be"
        "supported in future releases of django-drf-filepond."
        "0.5.x releases are the last to provide support for "
        "Python 2.7, 3.5, 3.6 and 3.7.",
        DjangoDrfFilepondDeprecationWarning,
        stacklevel=2,
    )
