'''
Setup some local application settings with local defaults.
This approach is based on the one shown in this blog post:

http://blog.muhuk.com/2010/01/26/developing-reusable-django-apps-app-settings.html#.W_Rkh-mYQ6U
'''
import os
from django.conf import settings

_app_prefix = 'DJANGO_DRF_FILEPOND_'

UPLOAD_TMP = getattr(settings, _app_prefix + 'UPLOAD_TEMP', 
                      os.path.join(settings.BASE_DIR, 'django_drf_filepond', 
                                   'uploads'))
