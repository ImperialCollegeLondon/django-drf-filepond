# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

import django_drf_filepond.drf_filepond_settings as local_settings


FILEPOND_UPLOAD_TMP = getattr(local_settings, 'UPLOAD_TMP',
                              os.path.join(
                                  settings.BASE_DIR,'filepond_uploads'))
storage = FileSystemStorage(location=FILEPOND_UPLOAD_TMP)

LOG = logging.getLogger(__name__)

def get_upload_path(instance, filename):
    return os.path.join(instance.upload_id, filename)

class TemporaryUpload(models.Model):
    
    FILE_DATA = 'F'
    URL = 'U'
    UPLOAD_TYPE_CHOICES = (
        (FILE_DATA, 'Uploaded file data'),
        (URL, 'Remote file URL'),
    )
    
    # The unique ID returned to the client and the name of the temporary 
    # directory created to hold file data
    upload_id = models.CharField(primary_key=True, max_length=22, 
                               validators=[MinLengthValidator(22)])
    # The unique ID used to store the file itself
    file_id = models.CharField(max_length=22, 
                               validators=[MinLengthValidator(22)])
    file = models.FileField(storage=storage, upload_to=get_upload_path)
    upload_name = models.CharField(max_length=512)
    uploaded = models.DateTimeField(auto_now_add=True)
    upload_type = models.CharField(max_length = 1, 
                                   choices=UPLOAD_TYPE_CHOICES)
    
    def get_file_path(self):
        return self.file.path

class StoredUpload(models.Model):
        
    # The unique upload ID assigned to this file when it was originally 
    # uploaded (or retrieved from a remote URL) 
    upload_id = models.CharField(primary_key=True, max_length=22, 
                               validators=[MinLengthValidator(22)])
    # The file name and path (relative to the base file store directory 
    # as set by DJANGO_DRF_FILEPOND_FILE_STORE_PATH).
    file_path = models.CharField(max_length=2048)
    uploaded = models.DateTimeField()
    stored = models.DateTimeField(auto_now_add=True)
    
    def get_absolute_file_path(self):
        return os.path.join(local_settings.FILE_STORE_PATH, self.file_path)
    
# When a TemporaryUpload record is deleted, we need to delete the 
# corresponding file from the filesystem by catching the post_delete signal.
@receiver(post_delete, sender=TemporaryUpload)
def delete_temp_upload_file(sender, instance, **kwargs):
    # Check that the file parameter for the instance is not None
    # and that the file exists and is not a directory! Then we can delete it
    LOG.debug('*** post_delete signal handler called. Deleting file.')
    if instance.file:
        if (os.path.exists(instance.file.path) and 
            os.path.isfile(instance.file.path)):
            os.remove(instance.file.path)
    
    if local_settings.DELETE_UPLOAD_TMP_DIRS:
        file_dir = os.path.join(storage.location, instance.upload_id)
        if(os.path.exists(file_dir) and os.path.isdir(file_dir)):
            os.rmdir(file_dir)
            LOG.debug('*** post_delete signal handler called. Deleting temp '
                      'dir that contained file.')

