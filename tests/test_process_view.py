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
from django.core.files.base import ContentFile
from django_drf_filepond import drf_filepond_settings

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
        tmp_upload_dir = drf_filepond_settings.UPLOAD_TMP
        self.uploaddir_exists_pre_test = os.path.exists(tmp_upload_dir)
        (encoded_form, content_type) = self._get_encoded_form('testfile.dat')
        
        response = self.client.post(reverse('process'),
                                data=encoded_form, content_type=content_type)
        #LOG.debug(response)
        # If the directory for temp file upload didn't exist when we started
        # the test then it's just been created so we can remove it and its
        # contents. 
        if not self.uploaddir_exists_pre_test:
            if hasattr(response, 'data'):
                filepath = os.path.join(tmp_upload_dir, response.data)
                if os.path.exists(filepath):
                    LOG.debug('Removing generated file <%s>' % filepath)
                    os.remove(filepath)
            LOG.debug('Removing created directory <%s>' % tmp_upload_dir)
            os.removedirs(tmp_upload_dir)

        self.assertEqual(response.status_code, 200, 
                         'Response received status code <%s> instead of 200.'
                         % (response.status_code))
        
        data = response.data
        # If the temp upload directory did exist at the start of the test, 
        # it will still be present now so we can just remove the created 
        # temporary upload file from it.
        upload_file_path = os.path.join(tmp_upload_dir, data)
        if os.path.exists(upload_file_path):
            LOG.debug('Removing generated file <%s> - directory was already '
                      'present so leaving in place' % upload_file_path)
            os.remove(upload_file_path)
        
        self.assertEqual(len(data), 22, 
                         'Response data is not of the correct length.')
    
    def test_process_invalid_storage_location(self):
        old_storage = views.storage
        views.storage = FileSystemStorage(location='/django_test')
        (encoded_form, content_type) = self._get_encoded_form('testfile.dat')
        
        rf = RequestFactory()
        req = rf.post(reverse('process'),
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
        req = rf.post(reverse('process'), data=enc_form,
                      content_type='multipart/form-data; boundary=abc')
        pv = views.ProcessView.as_view()
        response = pv(req)
        self.assertEqual(response.status_code, 400, 'Expecting 400 error due'
                         ' to invalid data being provided.')
        self.assertTrue('detail' in response.data, 
                      'Error detail missing in response.')
        self.assertIn(response.data['detail'], ('Invalid request data has '
                    'been provided.'))
    
    def test_upload_non_file_data(self):
        cf = ContentFile(self.test_data.read(), name='test.txt')
        upload_form = {'filepond': cf}
        enc_form = encode_multipart('abc', upload_form)
        rf = RequestFactory()
        req = rf.post(reverse('process'), data=enc_form,
                      content_type='multipart/form-data; boundary=abc')
        req.FILES['filepond'] = cf
        pv = views.ProcessView.as_view()
        response = pv(req)
        self.assertEqual(response.status_code, 400, 'Expecting 400 error due'
                         ' to non-file data being provided.')
        self.assertTrue('detail' in response.data, 
                      'Error detail missing in response.')
        self.assertIn(response.data['detail'], ('Invalid data type has been '
                        'parsed.'))
        
    
    def _get_encoded_form(self, filename):
        f = SimpleUploadedFile(filename, self.test_data.read())
        upload_form = {'filepond':f}
        
        boundary = str(uuid.uuid4()).replace('-','')
        
        encoded_form = encode_multipart(boundary, upload_form)
        
        content_type = ('multipart/form-data; boundary=%s' % (boundary))
        
        return (encoded_form, content_type)
        