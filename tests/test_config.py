'''
Test the configuration for the django_drf_filepond app.

Ensure that if we don't set DJANGO_DRF_FILEPOND_UPLOAD_TMP in our
Django project configuration, that it gets set to a sensible default.
'''
import logging
import os

from django.test import TestCase
from django.conf import settings
from six.moves import reload_module

from django_drf_filepond import views
import django_drf_filepond
from django.test.utils import override_settings

import django_drf_filepond.drf_filepond_settings as local_settings

LOG = logging.getLogger(__name__)


class AppSettingsTestCase(TestCase):

    @classmethod
    def tearDownClass(cls):
        super(AppSettingsTestCase, cls).tearDownClass()
        reload_module(local_settings)

    def test_default_upload_config(self):
        reload_module(local_settings)
        from django_drf_filepond import models
        upload_tmp = models.storage.location
        LOG.debug('We have a settings value of: %s' % (upload_tmp))
        self.assertEqual(upload_tmp,
                         os.path.join(local_settings.BASE_DIR,
                                      'filepond_uploads'))

    @override_settings()
    def test_upload_config_no_base_dir(self):
        LOG.debug('******SETTINGS.BASE_DIR: %s' % settings.BASE_DIR)
        del settings.BASE_DIR
        reload_module(local_settings)
        LOG.debug('******LOCAL_SETTINGS.BASE_DIR: %s'
                  % local_settings.BASE_DIR)
        up_dir = os.path.join(local_settings.BASE_DIR, 'filepond_uploads')
        LOG.debug('We have a settings value of: %s' % (up_dir))
        app_base = os.path.dirname(django_drf_filepond.__file__)
        self.assertEqual(up_dir,
                         os.path.join(app_base, 'filepond_uploads'))

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
