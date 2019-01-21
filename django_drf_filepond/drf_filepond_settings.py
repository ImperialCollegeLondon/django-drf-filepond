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

# The location where uploaded files are temporarily stored. At present, 
# this must be a subdirectory of settings.BASE_DIR
UPLOAD_TMP = getattr(settings, _app_prefix+'UPLOAD_TMP',
                     os.path.join(settings.BASE_DIR,'filepond_uploads'))

# Setting to control whether the temporary directories created for file 
# uploads are removed when an uploaded file is deleted
DELETE_UPLOAD_TMP_DIRS = getattr(settings, 
                                 _app_prefix+'DELETE_UPLOAD_TMP_DIRS', True)

# The file storage location used by the top-level application. This needs to 
# be set if the load endpoint is going to be used to access files that have 
# been permanently stored after being uploaded as TemporaryUpload objects.
FILE_STORE_PATH = getattr(settings, _app_prefix+'FILE_STORE_PATH', None)