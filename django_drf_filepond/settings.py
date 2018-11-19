import os
from django.conf import settings

FILEPOND_UPLOAD_TMP = getattr(settings, 'FILEPOND_UPLOAD_TMP', 
                              os.path.join(settings.BASE_DIR, 'uploads', 
                                           'filepond', 'tmp'))