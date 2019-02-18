from django.apps import AppConfig

import os
import logging
from django.conf import settings
import django_drf_filepond.drf_filepond_settings as local_settings

LOG = logging.getLogger(__name__)

class DjangoDrfFilepondConfig(AppConfig):
    name = 'django_drf_filepond'
    verbose_name = 'FilePond Server-side API'
    
    def ready(self):
        upload_tmp = getattr(local_settings, 'UPLOAD_TMP',
                             os.path.join(
                                 settings.BASE_DIR,'filepond_uploads'))
        LOG.debug('Upload temp directory from top level settings: <%s>'
                  % (upload_tmp))
        
        # Check if the temporary file directory is available and if not
        # create it.
        if not os.path.exists(local_settings.UPLOAD_TMP):
            LOG.warning('Filepond app init: Creating temporary file '
                     'upload directory <%s>' % local_settings.UPLOAD_TMP)
            os.makedirs(local_settings.UPLOAD_TMP, mode=0o700)
        else:
            LOG.debug('Filepond app init: Temporary file upload '
                      'directory already exists')

        file_store = getattr(local_settings, 'FILE_STORE_PATH', None)
        if file_store:
            if not os.path.exists(file_store):
                LOG.warning('Filepond app init: Creating file store '
                            'directory <%s>...' % file_store)
                os.makedirs(file_store, mode=0o700)
            else:
                LOG.debug('Filepond app init: File store path already '
                          'exists')