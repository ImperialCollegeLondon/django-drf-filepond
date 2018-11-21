'''
Setup some local application settings with local defaults.
This approach is based on the one shown in this blog post:

http://blog.muhuk.com/2010/01/26/developing-reusable-django-apps-app-settings.html#.W_Rkh-mYQ6U

******** Settings in this file are not currently being used due to an 
******** issue with dynamically setting up the sotrage location in the 
******** FileSystemStorage class. For now, you must set 
******** DJANGO_DRF_FILEPOND_UPLOAD_TMP in your top level app settings.
'''
import os
from django.conf import settings

_app_prefix = 'DJANGO_DRF_FILEPOND_'

UPLOAD_TMP = None
UPLOAD_TMP_DEFAULT = os.path.join(settings.BASE_DIR, 
                                  'django_drf_filepond', 'uploads')
