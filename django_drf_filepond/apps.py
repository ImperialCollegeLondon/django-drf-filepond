from django.apps import AppConfig

import importlib
import os
import logging
import six
import errno
import django_drf_filepond.drf_filepond_settings as local_settings

LOG = logging.getLogger(__name__)


class DjangoDrfFilepondConfig(AppConfig):
    name = 'django_drf_filepond'
    verbose_name = 'FilePond Server-side API'

    def ready(self):
        # Get BASE_DIR and process to ensure it works across platforms
        # Handle py3.5 where pathlib exists but os.path.join can't accept a
        # pathlib object (ensure we always pass a string to os.path.join)
        BASE_DIR = local_settings.BASE_DIR
        try:
            from pathlib import Path
            if isinstance(BASE_DIR, Path):
                BASE_DIR = str(BASE_DIR)
        except ImportError:
            pass

        upload_tmp = getattr(
            local_settings, 'UPLOAD_TMP',
            os.path.join(BASE_DIR, 'filepond_uploads'))

        LOG.debug('Upload temp directory from top level settings: <%s>'
                  % (upload_tmp))

        # Check if the temporary file directory is available and if not
        # create it.
        if not os.path.exists(local_settings.UPLOAD_TMP):
            LOG.warning('Filepond app init: Creating temporary file '
                        'upload directory <%s>' % local_settings.UPLOAD_TMP)
            # exist_ok=True has been added here to address an assumed race
            # condition when running multiple workers - see #104.
            # Since exist_ok isn't supported in Python2.7, a temporary
            # addition has been put in place to address this, it will be
            # removed when 2.7 support is dropped.
            if six.PY2:
                try:
                    os.makedirs(local_settings.UPLOAD_TMP, mode=0o700)
                except OSError as e:
                    # If the error is not caused by the directory existing
                    # then re-raise the original error.
                    if e.errno != errno.EEXIST:
                        raise
            else:
                os.makedirs(local_settings.UPLOAD_TMP, mode=0o700,
                            exist_ok=True)
        else:
            LOG.debug('Filepond app init: Temporary file upload '
                      'directory already exists')

        # See if we're using a local file store or django-storages
        # If the latter, we create an instance of the storage class
        # to make sure that it's available and dependencies are installed
        storage_class = getattr(local_settings, 'STORAGES_BACKEND', None)
        if storage_class:
            LOG.info('Using django-storages with backend [%s]'
                     % storage_class)
            (modname, clname) = storage_class.rsplit('.', 1)
            # Either the module import or the getattr to instantiate the
            # class will throw an exception if there's a problem
            # creating storage backend instance due to missing configuration
            # or dependencies.
            mod = importlib.import_module(modname)
            getattr(mod, clname)()
            LOG.info('Storage backend [%s] is available...' % storage_class)
        else:
            LOG.info('App init: no django-storages backend configured, '
                     'using default (local) storage backend if set, '
                     'otherwise you need to manage file storage '
                     'independently of this app.')

        file_store = getattr(local_settings, 'FILE_STORE_PATH', None)
        if file_store:
            if not os.path.exists(file_store):
                LOG.warning('Filepond app init: Creating file store '
                            'directory <%s>...' % file_store)
                os.makedirs(file_store, mode=0o700)
            else:
                LOG.debug('Filepond app init: File store path already '
                          'exists')
        else:
            if not storage_class:
                # As highlighted in #97, it's possible that users of the
                # library will want to handle permanent file storage manually.
                # In this case, both FILE_STORE_PATH and STORAGES_BACKEND may
                # remain unset. Rather than raising an error here, we now
                # simply provide a warning and check for existence of one of
                # the required configuration options when API calls are made.
                LOG.warning(
                    'You have not set either %sFILE_STORE_PATH or '
                    '%sSTORAGES_BACKEND. It is assumed that you are handling '
                    'permanent storage of files (after they are uploaded to '
                    'django-drf-filepond from the filepond client) manually. '
                    'If this is not the case, you need to set one of these '
                    'settings.' %
                    (local_settings._app_prefix, local_settings._app_prefix))
