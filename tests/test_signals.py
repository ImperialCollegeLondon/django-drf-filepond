import logging
import os
from django_drf_filepond import models
from django.test.testcases import TestCase
from django_drf_filepond.models import TemporaryUpload, delete_temp_upload_file
from django.core.files.uploadedfile import SimpleUploadedFile
from tempfile import mkstemp, mkdtemp
from django.core.files.storage import FileSystemStorage

# On Python 3.3+ we have unittest.Mock in the main system library
# On 2.7 it is installed as a dependency.
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

LOG = logging.getLogger(__name__)


class SignalsTestCase(TestCase):

    def test_del_tmp_upload_file(self):
        # Create a temporary file
        tmp_dir = mkdtemp(prefix='django_test_')
        self.assertTrue(os.path.exists(tmp_dir),
                        'Test temp file was not created.')
        tmp_dir_split = tmp_dir.rsplit(os.sep, 1)
        _, path = mkstemp(suffix='.txt', prefix='django_test_', text=True)
        self.assertTrue(os.path.exists(path),
                        'Test temp file was not created.')

        # Mock a TemporaryUpload instance object
        tu = Mock(spec=TemporaryUpload)
        upload_file = Mock(spec=SimpleUploadedFile)
        models.storage = Mock(spec=FileSystemStorage)
        models.storage.location = tmp_dir_split[0]

        upload_file.path = path
        tu.upload_id = tmp_dir_split[1]
        tu.file = upload_file
        delete_temp_upload_file(None, tu)
        self.assertFalse(os.path.exists(path), 'Test temp file was not '
                         'removed by the signal handler.')
