from django.apps import AppConfig

import os
import logging
import django_drf_filepond.drf_filepond_settings as settings

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class DjangoDrfFilepondConfig(AppConfig):
    name = 'django_drf_filepond'
    verbose_name = 'FilePond Server-side API'
    
    def ready(self):
        # Check if the temporary file directory is available and if not
        # create it.
        if not os.path.exists(settings.UPLOAD_TMP):
            LOG.info('Filepond app: Creating temporary file upload '
                     'directory <%s>...' % settings.UPLOAD_TMP)
            os.makedirs(settings.UPLOAD_TMP, mode=0o700)
