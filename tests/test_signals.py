import logging
import os
from django_drf_filepond import models
from django.test.testcases import TestCase
from unittest.mock import Mock
from django_drf_filepond.models import TemporaryUpload, delete_temp_upload_file
from django.core.files.uploadedfile import SimpleUploadedFile
from tempfile import mkstemp

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class SignalsTestCase(TestCase):
    
    def test_del_tmp_upload_file(self):
        # Create a temporary file
        _, path = mkstemp(suffix='.txt', prefix='django_test_', text=True)
        self.assertTrue(os.path.exists(path), 
                        'Test temp file was not created.')
        
        # Mock a TemporaryUpload instance object
        tu = Mock(spec=TemporaryUpload)
        upload_file = Mock(spec=SimpleUploadedFile)
        upload_file.path = path
        tu.file = upload_file
        delete_temp_upload_file(None, tu)
        self.assertFalse(os.path.exists(path),
                    'Test temp file was not removed by the signal handler.')