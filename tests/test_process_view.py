from io import BytesIO
import logging
import os
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import encode_multipart, RequestFactory
from django.urls import reverse

from django_drf_filepond import drf_filepond_settings
import django_drf_filepond.views as views
from tests.utils import remove_file_upload_dir_if_required

LOG = logging.getLogger(__name__)


class ProcessTestCase(TestCase):

    def setUp(self):
        # Create some random data to test upload.
        data = BytesIO()
        data.write(os.urandom(16384))
        self.test_data = data

    def test_process_data(self):
        self._process_data()

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
        self.assertEqual(
            response.data,
            'The file upload path settings are not configured correctly.',
            ('Expecting error showing path settings are configured '
             'incorrectly.'))

    def test_process_invalid_data(self):
        upload_form = {'somekey':
                       SimpleUploadedFile('test.txt', self.test_data.read())}
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

    # Based on the modification for issue #4, test that we can successfully
    # handle an upload that provides its data under a field name that is not
    # the default "filepond" and that an error is thrown when an invalid
    # name is expected
    def test_process_data_different_field_name(self):
        self._process_data('somefield')

    def test_process_data_invalid_different_field_name(self):
        upload_form = {'somekey': SimpleUploadedFile(
            'test.txt', self.test_data.read()), 'fp_upload_field': 'somekey2'
        }
        boundary = str(uuid.uuid4()).replace('-', '')
        enc_form = encode_multipart(boundary, upload_form)

        rf = RequestFactory()
        req = rf.post(reverse('process'), data=enc_form,
                      content_type='multipart/form-data; boundary=%s'
                      % boundary)
        pv = views.ProcessView.as_view()
        response = pv(req)
        self.assertEqual(response.status_code, 400, 'Expecting 400 error due'
                         ' to invalid data being provided.')
        self.assertTrue('detail' in response.data,
                        'Error detail missing in response.')
        self.assertIn(response.data['detail'], ('Invalid request data has '
                                                'been provided.'))

    def _process_data(self, upload_field_name=None):
        tmp_upload_dir = drf_filepond_settings.UPLOAD_TMP
        self.uploaddir_exists_pre_test = os.path.exists(tmp_upload_dir)
        (encoded_form, content_type) = self._get_encoded_form(
            'testfile.dat', upload_field_name)

        response = self.client.post(
            reverse('process'),
            data=encoded_form, content_type=content_type)

        # Attempt created file/directory removal before assert statements
        # so that we can clean up as far as possible at this stage.
        if hasattr(response, 'data'):
            dir_path = os.path.join(tmp_upload_dir, response.data)
            if len(response.data) == 22 and os.path.exists(dir_path):
                dir_list = os.listdir(dir_path)
                if len(dir_list) == 1 and len(dir_list[0]) == 22:
                    file_path = os.path.join(dir_path, dir_list[0])
                    LOG.debug('Removing generated file <%s>' % file_path)
                    os.remove(file_path)
                    LOG.debug('Removing temporary directory <%s>'
                              % dir_path)
                    os.rmdir(dir_path)
                else:
                    LOG.warning('Name of uploaded file in the temp '
                                'directory doesn\'t have 22 chars, '
                                'not deleting the file')
            else:
                LOG.error('Couldn\'t proceed with file deleting since the '
                          'response received was not the right length (22)')

        remove_file_upload_dir_if_required(self.uploaddir_exists_pre_test,
                                           tmp_upload_dir)

        self.assertEqual(response.status_code, 200,
                         'Response received status code <%s> instead of 200.'
                         % (response.status_code))

        self.assertTrue(hasattr(response, 'data'),
                        ('The response does not contain a data attribute.'))

        self.assertEqual(len(response.data), 22,
                         'Response data is not of the correct length.')

    def _get_encoded_form(self, filename, upload_field_name=None):
        f = SimpleUploadedFile(filename, self.test_data.read())
        if upload_field_name:
            upload_form = {upload_field_name: f,
                           'fp_upload_field': upload_field_name}
        else:
            upload_form = {'filepond': f}

        boundary = str(uuid.uuid4()).replace('-', '')

        encoded_form = encode_multipart(boundary, upload_form)

        content_type = ('multipart/form-data; boundary=%s' % (boundary))

        return (encoded_form, content_type)
