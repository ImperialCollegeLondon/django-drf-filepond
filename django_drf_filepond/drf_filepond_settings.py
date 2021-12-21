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
import django_drf_filepond
import os
from django.conf import settings

_app_prefix = 'DJANGO_DRF_FILEPOND_'

# BASE_DIR is assumed to be present in the core project settings. However,
# in case it isn't, we check here and set a local BASE_DIR to the
# installed app base directory to use as an alternative.
BASE_DIR = os.path.dirname(django_drf_filepond.__file__)
if hasattr(settings, 'BASE_DIR'):
    # If BASE_DIR is set in the main settings, get it and process it to
    # handle py3.5 where pathlib exists but os.path.join can't accept a
    # pathlib object (ensure we always pass a string to os.path.join)
    BASE_DIR = settings.BASE_DIR
    try:
        from pathlib import Path
        if isinstance(BASE_DIR, Path):
            BASE_DIR = str(BASE_DIR)
    except ImportError:
        pass

# The location where uploaded files are temporarily stored. At present,
# this must be a subdirectory of settings.BASE_DIR
UPLOAD_TMP = getattr(settings, _app_prefix+'UPLOAD_TMP',
                     os.path.join(BASE_DIR, 'filepond_uploads'))

# Setting to control whether the temporary directories created for file
# uploads are removed when an uploaded file is deleted
DELETE_UPLOAD_TMP_DIRS = getattr(settings,
                                 _app_prefix+'DELETE_UPLOAD_TMP_DIRS', True)

# Specifies the django-storages backend to be used. See the list at:
# https://django-storages.readthedocs.io
# If this is not set, then the default local filesystem backend is used.
# If you set this parameter, you also need to set the relevant parameters
# for your chosen backend as described in the django-storages documentation.
STORAGES_BACKEND = getattr(settings, _app_prefix+'STORAGES_BACKEND', None)

# The file storage location used by the top-level application. This needs to
# be set if the load endpoint is going to be used to access files that have
# been permanently stored after being uploaded as TemporaryUpload objects.
# If you're using django-storages, this path is the base path to be used
# on the backend storage.
# If STORAGES_BACKEND is provided, this MUST be set
# If you're not using a STORAGES_BACKEND and this is NOT set, you can't use
# django-drf-filepond's file management and the api.store_upload function
# will not be usable - you will need to manage file storage in your code.
FILE_STORE_PATH = getattr(settings, _app_prefix+'FILE_STORE_PATH', None)

# If you want to use an external directory (a directory outside of your
# project directory) to store temporary uploads, this setting needs to be
# set to true. By default it is False to prevent uploads being stored
# elsewhere.
ALLOW_EXTERNAL_UPLOAD_DIR = getattr(settings,
                                    _app_prefix+'ALLOW_EXTERNAL_UPLOAD_DIR',
                                    False)
# Optional permissions settings for each endpoint.
PERMISSION_CLASSES = getattr(settings, _app_prefix+'PERMISSION_CLASSES', {})

# Temporary filepond uploads larger than a certain size are broken up into
# "chunks" to be sent from the client to the server. This setting DOES NOT
# control the size of these chunks - they are instead controlled from the
# client side by specifying the chunkSize property (see filepond server
# properties: https://pqina.nl/filepond/docs/api/instance/properties/#server)
#
# This setting controls the way that chunks are read when django-drf-filepond
# saves a chunked temporary upload on the server to a complete file. Chunks
# are stored to individual chunk files on the server that when combined make
# up the complete file being uploaded. When the upload from the client of all
# chunks forming a full file is complete, the server combines the chunks into
# a full file - to do this, it reads in the data from the chunk files in
# blocks and writes them out to the complete file on disk. This setting
# controls the size of these blocks, or chunks.
#
# For most users the default setting should be fine, however, this ultimately
# controls how much memory is used (beyond that required for the original
# data upload) when storing files. In the original implementation, all chunk
# data was read in at once before writing the file content out to disk as a
# complete file ending up in usage of memory 2*<size of upload>.
# The default setting here of 1MB should result in total memory usage for
# upload handling of <size of upload>+1MB. If you are working with very
# large uploads, this may be inefficient and you may want to increase the
# setting, at the expense of temporarily using more memory, to improve
# efficiency.
TEMPFILE_READ_CHUNK_SIZE = getattr(settings,
                                   _app_prefix+'TEMPFILE_READ_CHUNK_SIZE',
                                   1048576)
