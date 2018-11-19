from django.apps import AppConfig

import os
import logging
import settings

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class DjangoDrfFilepondConfig(AppConfig):
    name = 'django_drf_filepond'
    verbose_name = 'FilePond Server-side API'
    
    def ready(self):
        # Check if the temporary file directory is available and if not
        # create it.
        if not os.path.exists(settings.FILEPOND_UPLOAD_TMP):
            LOG.info('Filepond app: Creating temporary file upload '
                     'directory <%s>...' % settings.FILEPOND_UPLOAD_TMP)
            os.makedirs(settings.FILEPOND_UPLOAD_TMP, mode=0700)
