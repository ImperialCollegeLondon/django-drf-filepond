# This module contains API functions exported through the top-level
# django_drf_filepond module.
#
# store_upload: used to move an upload from temporary storage to a permanent
#               storage location. This requires that you have the 
#               DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting set in your 
#               application's settings.py file.
#
import importlib
import logging
import ntpath
import os
import shutil

import django_drf_filepond.drf_filepond_settings as local_settings
from django.core.exceptions import ImproperlyConfigured
import re
import shortuuid
from django_drf_filepond.models import TemporaryUpload, StoredUpload

LOG = logging.getLogger(__name__)

# Store the temporary upload represented by upload_id to the specified  
# destination_file_path under the defined file store location as specified by 
# the DJANGO_DRF_FILEPOND_FILE_STORE_PATH configuration setting. 
# Files stored using this approach can subsequently be retrieved using the  
# load method defined in by the filepond server spec by using either the 
# 22-char upload_id or the value provided to the destination_file_path 
# parameter as a query string parameter using the "id" key.
def store_upload(upload_id, destination_file_path):
    """
    Store the temporary upload with the specified upload ID to the 
    destination_file_path. destination_file_path should be a directory only
    and not include the target name of the file. 
    
    If destination_file_name is not provided, the file
    is stored using the name it was originally uploaded with. If
    destination_file_name is provided, this is the name used to store the
    file. i.e. the file will be stored at 
        destination_file_path + destination_file_name
    """
    if ((not hasattr(local_settings, 'FILE_STORE_PATH')) 
        or
        (not local_settings.FILE_STORE_PATH)):
        raise ImproperlyConfigured('A required setting is missing in your '
                                   'application configuration.')
    
    
    id_fmt = re.compile('^([%s]){22}$' % (shortuuid.get_alphabet()))
    if not id_fmt.match(upload_id):
        errorMsg = ('The provided upload ID <%s> is of an invalid format.'
                    % upload_id) 
        LOG.error(errorMsg)
        raise ValueError(errorMsg)
    
    if not destination_file_path or destination_file_path == '':
        raise ValueError('No destination file path provided.')
    
    try:
        tu = TemporaryUpload.objects.get(upload_id=upload_id)
    except TemporaryUpload.DoesNotExist:
        raise ValueError('Record for the specified upload_id doesn\'t exist')

    destination_name = ntpath.basename(destination_file_path)
    destination_path = ntpath.dirname(destination_file_path)

    if storage_backend:
        return _store_upload_remote(destination_path, destination_name, tu)
    else:
        return _store_upload_local(destination_path, destination_name, tu)

def _store_upload_local(destination_file_path, destination_file_name, 
                        temp_upload):
    file_path_base = local_settings.FILE_STORE_PATH

    if not file_path_base or file_path_base == '':
        raise ValueError('The FILE_STORE_PATH is not set to a directory.')
    
    # Is this necessary? Checking on every file storage in case the directory
    # was removed but not sure that this is really necessary.
    if( (not os.path.exists(file_path_base)) or
        (not os.path.isdir(file_path_base)) ):
        raise FileNotFoundError(
            'The local output directory [%s] defined by FILE_STORE_PATH is '
            'missing.' % file_path_base)
    
    if destination_file_path.startswith(os.sep):
        destination_file_path = destination_file_path[1:]
    
    target_dir = os.path.join(file_path_base, 
                              os.path.dirname(destination_file_path))
    target_filename = destination_file_name
    if not target_filename:
        target_filename = temp_upload.upload_name
    if destination_file_path.endswith(os.sep):
        # Assume a directory was provided, get the file name from tu and 
        # add this to the provided path.
        destination_file_path += target_filename
        
    target_file_path = os.path.join(file_path_base, destination_file_path)
    
    # Check we're not about to overwrite anything
    if os.path.exists(target_file_path):
        LOG.error('File with specified name and path <%s> already exists' 
                  % destination_file_path)
        raise FileExistsError('The specified temporary file cannot be stored'
                              ' to the specified location - file exists.')
    
    su = StoredUpload(upload_id=temp_upload.upload_id, 
                      file_path=destination_file_path, 
                      uploaded=temp_upload.uploaded)
    
    try:
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        shutil.copy2(temp_upload.get_file_path(), target_file_path)
        su.save()
        temp_upload.delete()
    except IOError as e:
        LOG.error('Error moving temporary file to permanent storage location')
        raise e
    
    return su

def _store_upload_remote(destination_file_path, destination_file_name,
                         temp_upload):
    # Use the storage backend to write the file to the storage backend
    target_filename = destination_file_name
    if not target_filename:
        target_filename = temp_upload.upload_name
    
    su = None
    destination_file = os.path.join(destination_file_path, target_filename)
    try:
        opened_file = temp_upload.file.open()
        storage_backend.save(destination_file, opened_file)
        su = StoredUpload(upload_id=temp_upload.upload_id, 
                  file_path=destination_file, 
                  uploaded=temp_upload.uploaded)
        su.save()
        temp_upload.delete()
    except Exception as e:
        errorMsg = ('Error storing temporary upload to remote storage: [%s]'
                    % str(e))
        LOG.error(errorMsg)
        raise e
    finally:
        opened_file.close()
    
    return su

def _get_storage_backend(fq_classname):
    """
    Load the specified django-storages storage backend class. This is called
    regardless of whether a beckend is specified so if fq_classname is not 
    set, we just return None.
    
    fq_classname is a string specifying the fully-qualified class name of 
    the django-storages backend to use, e.g. 
        'storages.backends.sftpstorage.SFTPStorage'
    """
    if not fq_classname:
        return None

    (modname, clname) = fq_classname.rsplit('.', 1)
    # A test import of the backend storage class should have been undertaken
    # at app startup in django_drf_filepond.apps.ready so any failure
    # importing the backend should have been picked up then. 
    mod = importlib.import_module(modname)
    getattr(mod, clname)()
    LOG.info('Storage backend instance [%s] created...' % fq_classname)

storage_backend = _get_storage_backend(
    getattr(local_settings, 'STORAGES_BACKEND', None))
