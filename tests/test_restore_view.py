import logging
import os
# Switched to using Message rather than cgi.parse_header for parsing and
# checking header params since cgi is deprecated and will be removed in py3.13
from email.message import Message

import django_drf_filepond.drf_filepond_settings as drf_fp_settings
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.testcases import TestCase
from django.urls import reverse
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond.utils import _get_file_id

LOG = logging.getLogger(__name__)


#########################################################################
# The restore endpoint is used by the client to load a remote temporary
# file from the server.
# https://pqina.nl/filepond/docs/patterns/api/server/#restore
# The filepond client makes a restore request to the server which looks
# up the provided file upload ID in the TemporaryUpload table and then
# returns the file to the client if a valid upload ID was provided.
#
# test_restore_incorrect_method: Make POST/PUT/DELETE requests to the restore
#     endpoint to check that these are rejected with 405 method not allowed
#
# test_restore_invalid_param: Make a GET request to the restore endpoint
#     with an incorrect parameter name in the URL query string.
#
# test_restore_blank_id: Make a GET request to the restore endpoint with
#     a blank ID provided in the URL query string.
#
# test_restore_invalid_id_format: Make a GET request to the restore
#     endpoint with an invalid ID provided in the URL query string.
#
# test_restore_id_notfound_error: Make a GET request to the restore endpoint
#     with an ID that is a valid format but for which no record exists (404).
#
# test_restore_file_notfound_error: Make a GET request to the restore
#     endpoint with a valid ID but for which the file doesn't exist (404).
#
# test_restore_successful_request: Make a GET request to the restore endpoint
#     that is successful.
#
class RestoreTestCase(TestCase):

    def setUp(self):
        self.upload_id = _get_file_id()
        self.file_id = _get_file_id()
        self.file_content = ('This is some test file data for an '
                             'uploaded file.')
        self.fn = 'my_test_file.txt'
        uploaded_file = SimpleUploadedFile(self.fn,
                                           str.encode(self.file_content))
        tu = TemporaryUpload(upload_id=self.upload_id,
                             file_id=self.file_id,
                             file=uploaded_file, upload_name=self.fn,
                             upload_type=TemporaryUpload.FILE_DATA)
        tu.save()

    def test_restore_incorrect_method(self):
        response_post = self.client.post((reverse('restore') +
                                          ('?id=%s' % self.upload_id)))
        response_del = self.client.delete((reverse('restore') +
                                           ('?id=%s' % self.upload_id)))
        response_put = self.client.put((reverse('restore') +
                                        ('?id=%s' % self.upload_id)))
        self.assertEqual(response_post.status_code, 405)
        self.assertEqual(response_del.status_code, 405)
        self.assertEqual(response_put.status_code, 405)

    def test_restore_invalid_param(self):
        response = self.client.get((reverse('restore') + '?name='))
        self.assertContains(response, 'A required parameter is missing.',
                            status_code=400)

    def test_restore_blank_id(self):
        response = self.client.get((reverse('restore') + '?id='))
        self.assertContains(response, 'An invalid ID has been provided.',
                            status_code=400)

    def test_restore_invalid_id(self):
        response = self.client.get((reverse('restore') + '?id=sdfsdu732'))
        self.assertContains(response, 'An invalid ID has been provided.',
                            status_code=400)

    def test_restore_id_notfound_error(self):
        response = self.client.get((reverse('restore') +
                                    '?id=sdfsdu732defh754dhsrr2'))
        self.assertContains(response, 'Not found',
                            status_code=404)

    def test_restore_file_notfound_error(self):
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        os.remove(tu.get_file_path())
        response = self.client.get((reverse('restore') +
                                    ('?id=%s' % self.upload_id)))
        self.assertContains(response, 'Error reading file data...',
                            status_code=500)

    def test_restore_successful_request(self):
        response = self.client.get((reverse('restore') +
                                    ('?id=%s' % self.upload_id)))
        # We should get back the file data with a Content-Disposition
        # header similar to:
        # 'Content-Disposition: inline; filename="<file name>"'
        self.assertEqual(response.status_code, 200,
                         'An invalid response code has been received.')

        # Check the Content-Disposition header is valid
        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))

        msg = Message()
        msg['content-type'] = response['Content-Disposition']
        self.assertTrue(
            msg.get_param('filename'),
            'Content-Disposition header doesn\'t contain filename parameter')
        fname = msg.get_param('filename')
        self.assertEqual(
            self.fn, fname, ('Returned filename is not equal to the '
                             'provided filename value.'))

        self.assertEqual(response.content.decode(), self.file_content,
                         'The response data is invalid.')

    def tearDown(self):
        upload_tmp_base = getattr(settings,
                                  'DJANGO_DRF_FILEPOND_UPLOAD_TMP',
                                  None) or drf_fp_settings.UPLOAD_TMP
        upload_tmp_dir = os.path.join(upload_tmp_base, self.upload_id)
        upload_tmp_file = os.path.join(upload_tmp_dir, self.fn)
        if (os.path.exists(upload_tmp_file) and
                os.path.isfile(upload_tmp_file)):
            LOG.debug('Removing temporary file: <%s>' % upload_tmp_file)
            os.remove(upload_tmp_file)
        if (os.path.exists(upload_tmp_dir) and
                os.path.isdir(upload_tmp_dir)):
            LOG.debug('Removing temporary dir: <%s>' % upload_tmp_dir)
            os.rmdir(upload_tmp_dir)
