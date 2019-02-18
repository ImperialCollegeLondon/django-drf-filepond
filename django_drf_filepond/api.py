# This module contains API functions exported through the top-level
# django_drf_filepond module.
#
# store_upload: used to move an upload from temporary storage to a permanent
#               storage location. This requires that you have the 
#               DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting set in your 
#               application's settings.py file.
#
import logging
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
    if ((not hasattr(local_settings, 'FILE_STORE_PATH')) 
        or
        (not local_settings.FILE_STORE_PATH)
        or 
        (not os.path.exists(local_settings.FILE_STORE_PATH))
        or
        (not os.path.isdir(local_settings.FILE_STORE_PATH))):
        
        raise ImproperlyConfigured('A required setting is missing in your '
                                   'application configuration.')
    
    file_path_base = local_settings.FILE_STORE_PATH
    
    if not file_path_base or file_path_base == '':
        raise ValueError('The FILE_STORE_PATH is not set to a directory.')
    
    id_fmt = re.compile('^([%s]){22}$' % (shortuuid.get_alphabet()))
        
    if not id_fmt.match(upload_id):
        LOG.error('The provided upload ID <%s> is of an invalid format.'
                  % upload_id)
        raise ValueError('The provided upload ID is of an invalid format.')
            
    if not destination_file_path or destination_file_path == '':
        raise ValueError('No destination file path provided.')
    
    if destination_file_path.startswith(os.sep):
        destination_file_path = destination_file_path[1:]
        
    try:
        tu = TemporaryUpload.objects.get(upload_id=upload_id)
    except TemporaryUpload.DoesNotExist:
        raise ValueError('Record for the specified upload_id doesn\'t exist')
    
    target_dir = os.path.join(file_path_base, 
                              os.path.dirname(destination_file_path))
    if destination_file_path.endswith(os.sep):
        # Assume a directory was provided, get the file name from tu and 
        # add this to the provided path.
        destination_file_path += tu.upload_name
        
    target_file_path = os.path.join(file_path_base, destination_file_path)
    
    # Check we're not about to overwrite anything
    if os.path.exists(target_file_path):
        LOG.error('File with specified name and path <%s> already exists' 
                  % destination_file_path)
        raise FileExistsError('The specified temporary file cannot be stored'
                              ' to the specified location - file exists.')
    
    su = StoredUpload(upload_id=tu.upload_id,  
                      file_path=destination_file_path, uploaded=tu.uploaded)
    
    try:
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        shutil.copy2(tu.get_file_path(), target_file_path)
        su.save()
        tu.delete()
    except IOError as e:
        LOG.error('Error moving temporary file to permanent storage location')
        raise e
    
    return su