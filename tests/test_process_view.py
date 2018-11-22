from django.test import TestCase

import logging
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from django.urls import reverse
from django.test.client import encode_multipart, RequestFactory
import uuid
from django.core.files.storage import FileSystemStorage
import django_drf_filepond.views as views

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
        old_storage = views.storage
        views.storage = FileSystemStorage(location='/django_test')
        (encoded_form, content_type) = self._get_encoded_form('testfile.dat')
        
        rf = RequestFactory()
        req = rf.post(reverse('django_drf_filepond_process'),
                      data=encoded_form, content_type=content_type)
        pv = views.ProcessView.as_view()
        response = pv(req)
        views.storage = old_storage
        self.assertEqual(response.status_code, 500, 'Expecting 500 error due'
                         ' to invalid storage location.')
        self.assertEqual(response.data, ('The file upload path settings '
                        'are not configured correctly.'), ('Expecting error '
                        'showing path settings are configured incorrectly.'))
    
    def test_process_invalid_data(self):
        upload_form = {'somekey': SimpleUploadedFile('test.txt', 
                                                      self.test_data.read())}
        enc_form = encode_multipart('abc', upload_form)
        rf = RequestFactory()
        req = rf.post(reverse('django_drf_filepond_process'), data=enc_form,
                      content_type='multipart/form-data; boundary=abc')
        pv = views.ProcessView.as_view()
        response = pv(req)
        self.assertEqual(response.status_code, 400, 'Expecting 400 error due'
                         ' to invalid data being provided.')
        self.assertTrue('detail' in response.data, 
                      'Error detail missing in response.')
        self.assertIn(response.data['detail'], ('Invalid request data has '
                    'been provided.'))
        
    def _get_encoded_form(self, filename):
        f = SimpleUploadedFile(filename, self.test_data.read())
        upload_form = {'filepond':f}
        
        boundary = str(uuid.uuid4()).replace('-','')
        
        encoded_form = encode_multipart(boundary, upload_form)
        
        content_type = ('multipart/form-data; boundary=%s' % (boundary))
        
        return (encoded_form, content_type)
        