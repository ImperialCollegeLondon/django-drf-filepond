from django.apps import AppConfig

import os
import logging
from django.conf import settings

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class DjangoDrfFilepondConfig(AppConfig):
    name = 'django_drf_filepond'
    verbose_name = 'FilePond Server-side API'
    
    def ready(self):
        # Begin by updating the local_settings with any settings provided
        # via the main app settings.
        #local_settings.UPLOAD_TMP = getattr(settings, 
        #        local_settings._app_prefix + 'UPLOAD_TMP',
        #        local_settings.UPLOAD_TMP_DEFAULT)
        # 
        #LOG.debug('Upload temp directory after checking for provided '
        #          'parameter in settings is <%s>' % 
        #          (local_settings.UPLOAD_TMP))
        upload_tmp = getattr(settings, 'DJANGO_DRF_FILEPOND_UPLOAD_TMP',
                             os.path.join(settings.BASE_DIR,'filepond_uploads'))
        LOG.debug('Upload temp directory from top level settings: <%s>'
                  % (upload_tmp))
                
        # Check if the temporary file directory is available and if not
        # create it.
        ##### The upload directory is now checked for and created in 
        ##### the file upload view.
        #if not os.path.exists(local_settings.UPLOAD_TMP):
        #    LOG.info('Filepond app: Creating temporary file upload '
        #             'directory <%s>...' % local_settings.UPLOAD_TMP)
        #    os.makedirs(local_settings.UPLOAD_TMP, mode=0o700)
