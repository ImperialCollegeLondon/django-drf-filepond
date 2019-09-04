import logging
import os
from django.test.testcases import TestCase
import django_drf_filepond.models as models
import django_drf_filepond.drf_filepond_settings as local_settings
import django.conf
LOG = logging.getLogger(__name__)


#########################################################################
# Test that we can successfully import/instantiate the various models.
#
# test_models_attributes_upload_temp_from_settings: Check that the temp
#    upload directory is correctly read from settings into models.
#
# test_models_attributes_upload_temp_default: Check that the temp upload
#    directory is set to a sensible default when UPLOAD_TMP is not in settings.
#
class ModelsTestCase(TestCase):

    def test_models_attributes_upload_temp_from_settings(self):
        upload_temp_dir = models.FILEPOND_UPLOAD_TMP
        self.assertEqual(
            upload_temp_dir, local_settings.UPLOAD_TMP,
            'The upload temp directory in models is set to [%s] but '
            'expected it to be set to settings.DJANGO_DRF_FILEPOND_UPLOAD_TMP'
            '[%s]' % (upload_temp_dir, local_settings.UPLOAD_TMP))

    def test_models_attributes_upload_temp_default(self):
        del local_settings.UPLOAD_TMP
        default_upload_path = os.path.join(local_settings.BASE_DIR,
                                           'filepond_uploads')
        import django_drf_filepond.models
        try:
            self.assertEqual(
                django_drf_filepond.models.FILEPOND_UPLOAD_TMP,
                default_upload_path,
                'The upload temp directory in models is set to [%s] but '
                'expected it to be set to the default value [%s]'
                % (django_drf_filepond.models.FILEPOND_UPLOAD_TMP,
                   default_upload_path))
        finally:
            local_settings.UPLOAD_TMP = getattr(
                django.conf.settings, local_settings._app_prefix+'UPLOAD_TMP',
                os.path.join(local_settings.BASE_DIR, 'filepond_uploads'))
