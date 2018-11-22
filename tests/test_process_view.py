from django.test import TestCase

import logging
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from django.urls import reverse
from django.test.client import encode_multipart
import uuid
from unittest.mock import patch
from django.core.files.storage import FileSystemStorage
import django_drf_filepond.models as models

LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

class ProcessTestCase(TestCase):
    
    def setUp(self):
        # Create some random data to test upload.
        data = BytesIO()
        data.write(os.urandom(16384))
        self.test_data = data
    
    def test_process_data(self):
        (encoded_form, content_type) = self._get_encoded_form('testfile.dat')
        
        response = self.client.post(reverse('django_drf_filepond_process'),
                                data=encoded_form, content_type=content_type)
        LOG.debug(response)
        self.assertEqual(response.status_code, 200, 
                         'Response received status code <%s> instead of 200.'
                         % (response.status_code))
        
        data = response.data
        self.assertEqual(len(data), 22, 
                         'Response data is not of the correct length.')
    
    def test_process_invalid_storage_location(self):
        models.storage = FileSystemStorage(location='/django_test')
        (encoded_form, content_type) = self._get_encoded_form('testfile.dat')
        
        response = self.client.post(reverse('django_drf_filepond_process'),
                                data=encoded_form, content_type=content_type)
        self.assertEqual(response.status_code, 500, 'Expecting 500 error due'
                         ' to invalid storage location.')
        
    def _get_encoded_form(self, filename):
        f = SimpleUploadedFile(filename, self.test_data.read())
        upload_form = {'filepond':f}
        
        boundary = str(uuid.uuid4()).replace('-','')
        
        encoded_form = encode_multipart(boundary, upload_form)
        
        content_type = ('multipart/form-data; boundary=%s' % (boundary))
        
        return (encoded_form, content_type)
        