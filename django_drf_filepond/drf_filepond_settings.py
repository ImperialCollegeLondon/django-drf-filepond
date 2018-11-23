'''
Setup some local application settings with local defaults.
This approach is based on the one shown in this blog post:

http://blog.muhuk.com/2010/01/26/developing-reusable-django-apps-app-settings.html#.W_Rkh-mYQ6U

******** Settings in this file are not currently being used for core library
******** use due to an issue with dynamically setting up the storage  
******** location in the FileSystemStorage class. For now, you must set 
******** DJANGO_DRF_FILEPOND_UPLOAD_TMP in your top level app settings.
******** THIS IS CURRENTLY USED ONLY FOR INTEGRATION TESTS
'''
import os
from django.conf import settings

_app_prefix = 'DJANGO_DRF_FILEPOND_'

UPLOAD_TMP = getattr(settings, _app_prefix+'UPLOAD_TMP',
                     os.path.join(settings.BASE_DIR,'filepond_uploads'))
