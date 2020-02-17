import logging

from django.test.testcases import TestCase
from django_drf_filepond.views import _get_file_id
from django_drf_filepond.models import TemporaryUpload, StoredUpload
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
import django_drf_filepond.drf_filepond_settings as local_settings
import cgi
import os
import shutil
import django_drf_filepond

LOG = logging.getLogger(__name__)


#########################################################################
# The load endpoint is used by the client to load a remote stored file
# from the server. This is a file that has been stored using the
# django-drf-filepond library and is managed by the library.
# https://pqina.nl/filepond/docs/patterns/api/server/#load
# The filepond client makes a load request to the server containing an
# ID or a filename. The server looks up the provided file information in
# the StoredUpload table and returns the file to the client if a valid ID
# or filename have been provided.
#
# test_load_incorrect_method: Make POST/PUT/DELETE requests to the load
#     endpoint to check these are rejected with 405 method not allowed
#
# test_load_invalid_param: Make a GET request to the load endpoint
#     with an incorrect parameter name in the URL query string.
#
# test_load_blank_id: Make a GET request to the load endpoint with a
#     blank ID provided in the URL query string.
#
# test_load_id_notfound_error: Make a GET request to the load endpoint
#     with an ID that is not an upload ID or filename. (404).
#
# test_load_id_file_notfound_error: Make a GET request to the load
#     endpoint with a valid upload ID where the file doesn't exist (404).
#
# test_load_uploadid_successful_request: Make a GET request to the load
#     endpoint with an upload ID. The request is successful.
#
# test_load_filename_successful_request: Make a GET request to the load
#     endpoint with a filename. The request is successful.
#
# test_load_ambiguous_id_file: Make a GET request to the load endpoint
#     a 22-character ID in the URL query string that is a file name.
class LoadTestCase(TestCase):

    def _check_file_response(self, response, filename, file_content):
        self.assertEqual(response.status_code, 200,
                         'An invalid response code has been received.')

        # Check the Content-Disposition header is valid
        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue('filename' in cdisp[1], ('Content-Disposition'
                        ' header doesn\'t contain filename parameter'))
        fname = cdisp[1]['filename']
        self.assertEqual(filename, fname, ('Returned filename is not '
                         'equal to the provided filename value.'))

        test_file_content = file_content if type(file_content) == str \
            else file_content.decode()
        self.assertEqual(response.content.decode(), test_file_content,
                         'The response data is invalid.')

    @classmethod
    def setUpTestData(cls):
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        LOG.debug('File store path in %s setup: %s'
                  % (__name__, file_store_path))
        cls.FILE_STORE_PATH = file_store_path
        local_settings.STORAGES_BACKEND = None
        django_drf_filepond.api.storage_backend = None

    def setUp(self):
        # Set up an initial file upload
        self.upload_id = _get_file_id()
        self.file_id = _get_file_id()
        self.file_content = ('This is some test file data for an '
                             'uploaded file.')
        self.fn = 'my_test_file.txt'
        self.test_filename = 'sdf5dua32defh754dhsrr2'
        uploaded_file = SimpleUploadedFile(self.fn,
                                           str.encode(self.file_content))
        tu = TemporaryUpload(upload_id=self.upload_id,
                             file_id=self.file_id,
                             file=uploaded_file, upload_name=self.fn,
                             upload_type=TemporaryUpload.FILE_DATA)
        tu.save()

        # Now set up a stored version of this upload
        su = StoredUpload(upload_id=self.upload_id,
                          file=('%s'
                                     % (self.fn)),
                          uploaded=tu.uploaded)
        su.save()

    def test_load_incorrect_method(self):
        response_post = self.client.post((reverse('load') +
                                          ('?id=%s' % self.upload_id)))
        response_del = self.client.delete((reverse('load') +
                                           ('?id=%s' % self.upload_id)))
        response_put = self.client.put((reverse('load') +
                                        ('?id=%s' % self.upload_id)))
        self.assertEqual(response_post.status_code, 405)
        self.assertEqual(response_del.status_code, 405)
        self.assertEqual(response_put.status_code, 405)

    def test_load_invalid_param(self):
        response = self.client.get((reverse('load') + '?name='))
        self.assertContains(response, 'A required parameter is missing.',
                            status_code=400)

    def test_load_blank_id(self):
        response = self.client.get((reverse('load') + '?id='))
        self.assertContains(response, 'An invalid ID has been provided.',
                            status_code=400)

    def test_load_id_notfound_error(self):
        response = self.client.get((reverse('load') +
                                    ('?id=sdfsdu732defh754dhsrr2')))
        self.assertContains(response, 'Not found', status_code=404)

    def test_load_id_file_notfound_error(self):
        response = self.client.get((reverse('load') +
                                    ('?id=%s' % self.upload_id)))
        self.assertContains(response, 'Error accessing file, not found.',
                            status_code=404)

    def test_load_uploadid_successful_request(self):
        su = StoredUpload.objects.get(upload_id=self.upload_id)
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        su_target_dir = os.path.join(LoadTestCase.FILE_STORE_PATH,
                                     os.path.dirname(su.file.name))
        if not os.path.exists(su_target_dir):
            os.mkdir(su_target_dir)
        shutil.copy2(tu.get_file_path(), os.path.join(
            LoadTestCase.FILE_STORE_PATH, su.file.name))

        response = self.client.get((reverse('load') +
                                    ('?id=%s' % self.upload_id)))
        self._check_file_response(response, self.fn, self.file_content)

    def test_load_filename_successful_request(self):
        su = StoredUpload.objects.get(upload_id=self.upload_id)
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        su_target_dir = os.path.join(LoadTestCase.FILE_STORE_PATH,
                                     os.path.dirname(su.file.name))
        if not os.path.exists(su_target_dir):
            os.mkdir(su_target_dir)
        shutil.copy2(tu.get_file_path(), os.path.join(
            LoadTestCase.FILE_STORE_PATH, su.file.name))

        response = self.client.get((reverse('load') + '?id=%s' % self.fn))
        self._check_file_response(response, self.fn, self.file_content)

    def test_load_ambiguous_id_file(self):
        su = StoredUpload.objects.get(upload_id=self.upload_id)
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        su_target_dir = os.path.join(LoadTestCase.FILE_STORE_PATH,
                                     os.path.dirname(su.file.name))
        if not os.path.exists(su_target_dir):
            os.mkdir(su_target_dir)
        shutil.copy2(tu.get_file_path(), os.path.join(
            LoadTestCase.FILE_STORE_PATH, su.file.name))

        existing_path = os.path.join(LoadTestCase.FILE_STORE_PATH,
                                     su.file.name)
        existing_path_dir = os.path.dirname(existing_path)
        os.rename(existing_path,
                  os.path.join(existing_path_dir, self.test_filename))
        su.file.name = os.path.join(os.path.dirname(su.file.name),
                                    self.test_filename)
        su.save()
        response = self.client.get((reverse('load') +
                                    '?id=%s' % self.test_filename))
        self._check_file_response(response, self.test_filename,
                                  self.file_content)

    def test_load_filename_invalid_filestore_setting(self):
        su = StoredUpload.objects.get(upload_id=self.upload_id)
        fspath = local_settings.FILE_STORE_PATH
        local_settings.FILE_STORE_PATH = None
        try:
            response = self.client.get((reverse('load') + '?id=%s'
                                        % su.upload_id))
            self.assertContains(
                response,
                'The file upload settings are not configured correctly.',
                status_code=500)
        finally:
            local_settings.FILE_STORE_PATH = fspath

    def tearDown(self):
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        filestore_base = getattr(local_settings, 'FILE_STORE_PATH', None)
        upload_tmp_dir = os.path.join(upload_tmp_base, self.upload_id)
        upload_tmp_file = os.path.join(upload_tmp_dir, self.fn)
        test_file = os.path.join(filestore_base, self.test_filename)
        stored_file = os.path.join(filestore_base, self.fn)
        if (os.path.exists(upload_tmp_file) and
                os.path.isfile(upload_tmp_file)):
            LOG.debug('Removing temporary file: <%s>' % upload_tmp_file)
            os.remove(upload_tmp_file)
        if (os.path.exists(upload_tmp_dir) and
                os.path.isdir(upload_tmp_dir)):
            LOG.debug('Removing temporary dir: <%s>' % upload_tmp_dir)
            os.rmdir(upload_tmp_dir)
        if (os.path.exists(test_file) and os.path.isfile(test_file)):
            LOG.debug('Removing test file: <%s>' % test_file)
            os.remove(test_file)
        if (os.path.exists(stored_file) and os.path.isfile(stored_file)):
            LOG.debug('Removing stored file: <%s>' % stored_file)
            os.remove(stored_file)
