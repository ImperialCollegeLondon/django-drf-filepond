from io import BytesIO
import logging
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from django_drf_filepond import views
from django_drf_filepond.models import TemporaryUpload, storage
import django_drf_filepond.drf_filepond_settings as local_settings

LOG = logging.getLogger(__name__)


class RevertTestCase(TestCase):

    def setUp(self):
        # Set up a database containing a mock file record
        data = BytesIO()
        data.write(os.urandom(16384))
        self.base_upload_dir_at_startup = os.path.exists(storage.location)
        self.file_id = views._get_file_id()
        self.upload_id = views._get_file_id()
        test_file = SimpleUploadedFile(self.file_id, data.read())
        TemporaryUpload.objects.create(
            upload_id=self.upload_id,
            file_id=self.file_id, file=test_file,
            upload_name='testfile.txt',
            upload_type=TemporaryUpload.FILE_DATA)

    def tearDown(self):
        # Check that temp files in the storage directory have been removed
        upload_dir_to_check = os.path.join(storage.location, self.upload_id)
        upload_file_to_check = os.path.join(upload_dir_to_check, self.file_id)
        if (os.path.exists(upload_file_to_check) and
                os.path.isfile(upload_file_to_check)):
            os.remove(upload_file_to_check)
        if (os.path.exists(upload_dir_to_check) and
                os.path.isdir(upload_dir_to_check)):
            os.rmdir(upload_dir_to_check)

        # If the base upload dir didn't exist at startup, we remove it now
        if not self.base_upload_dir_at_startup:
            if len(os.listdir(storage.location)) == 0:
                LOG.debug('Removing base upload directory since it was '
                          'not present at start of test run.')
                os.rmdir(storage.location)
            else:
                LOG.warning('Base upload directory wasn\'t present at '
                            'start of tests but can\'t delete it because '
                            'it\'s not empty.')
        else:
            LOG.debug('Upload directory was present at start of test run '
                      'so not removing the directory.')

    def test_revert(self):
        # Check that our record is in the database
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)

        # Check that the file exists
        file_path = tu.get_file_path()
        self.assertTrue(os.path.exists(file_path),
                        'Test file to remove doesn\'t exist.')

        response = self.client.delete(reverse('revert'),
                                      data=str(self.upload_id),
                                      content_type='text/plain')
        self.assertEqual(response.status_code, 204,
                         'Expecting no content response code.')

        # The file deletion signal doesn't seem to be called when running
        # tests whereas it is called when running the app behind a regular
        # server. For now, deleting the file manually here.
        # *** The signal handler DOES now seem to be working as expected...
        # os.remove(file_path)

        # Check that the file was removed
        self.assertFalse(os.path.exists(file_path),
                         'The test file wasn\'t removed.')

    def test_revert_no_delete_dir(self):
        local_settings.DELETE_UPLOAD_TMP_DIRS = False
        # Check that our record is in the database
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)

        # Check that the file exists
        file_path = tu.get_file_path()
        self.assertTrue(os.path.exists(file_path),
                        'Test file to remove doesn\'t exist.')

        response = self.client.delete(
            reverse('revert'),
            data=str(self.upload_id), content_type='text/plain')
        self.assertEqual(response.status_code, 204,
                         'Expecting no content response code.')

        # Check that the file was removed but the directory was not
        self.assertFalse(os.path.exists(file_path),
                         'The test file wasn\'t removed.')
        self.assertTrue(os.path.exists(os.path.dirname(file_path)),
                        'The test file temp dir was unexpectedly removed.')
