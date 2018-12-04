'''
Test the configuration for the django_drf_filepond app.

Ensure that if we don't set DJANGO_DRF_FILEPOND_UPLOAD_TMP in our
Django project configuration, that it gets set to a sensible default.   
'''
import logging
import os
from django.apps import apps
from django.conf import settings
from django.test import TestCase, override_settings
from django_drf_filepond import models
from django_drf_filepond import views
from imp import reload

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class AppSettingsTestCase(TestCase):
    
    def test_default_upload_config(self):
        upload_tmp = models.storage.location
        LOG.debug('We have a settings value of: %s' % (upload_tmp))
        self.assertEqual(upload_tmp, 
                         os.path.join(settings.BASE_DIR, 
                                      'filepond_uploads'))
    
    def test_file_id(self):
        file_id = views._get_file_id()
        self.assertEqual(len(file_id), 22, 
                         'Incorrect length for generated file ID.')
    
    def test_file_id_clashes(self):
        GENERATED_IDS = 5000
        LOG.debug('Generating list of many file ids...')
        file_ids = [views._get_file_id() for _ in range(GENERATED_IDS)]
        file_id_set = set(file_ids)
        LOG.debug('File id list generated...')
        self.assertEqual(len(file_id_set), GENERATED_IDS, 'There were '
                         'clashes in the generated file IDs!')