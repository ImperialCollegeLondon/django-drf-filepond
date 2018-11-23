from django.test import TestCase

import logging
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond import views
from django.core.files.uploadedfile import InMemoryUploadedFile,\
    SimpleUploadedFile
from django.urls import reverse
from io import BytesIO
import os
from unittest import mock

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class RevertTestCase(TestCase):
    
    def setUp(self):
        # Set up a database containing a mock file record
        data = BytesIO()
        data.write(os.urandom(16384))
        self.file_id = views._get_file_id()
        test_file = SimpleUploadedFile(self.file_id, data.read())
        TemporaryUpload.objects.create(file_id=self.file_id, 
                    file=test_file, upload_name='testfile.txt',
                    upload_type=TemporaryUpload.FILE_DATA)
        
    
    def test_revert(self):
        # Check that our record is in the database
        TemporaryUpload.objects.get(file_id=self.file_id)
        response = self.client.delete(reverse('django_drf_filepond_revert'),
                        data=str(self.file_id), content_type='text/plain')
        self.assertEqual(response.status_code, 204, 
                         'Expecting no content response code.')
        