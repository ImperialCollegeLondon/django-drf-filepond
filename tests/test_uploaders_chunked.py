from io import BytesIO
import logging
import os

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django_drf_filepond.models import TemporaryUploadChunked
from django_drf_filepond.utils import _get_file_id
from rest_framework.request import Request

from django_drf_filepond.uploaders import FilepondChunkedFileUploader, storage
import django_drf_filepond
from six import ensure_text, ensure_binary

from tests.utils import _setupRequestData, prep_response

# Python 2/3 support
try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

# There's no built in FileNotFoundError in Python 2
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

LOG = logging.getLogger(__name__)
#
# This test class tests the functionality of the FilepondChunkedFileUploader
# class in the uploaders module. This class handles chunked upload of files
# according to the method described in filepond's server documentation:
# https://pqina.nl/filepond/docs/patterns/api/server/#process-chunks
#
# TESTS FOR TOP-LEVEL handle_upload FUNCTION
# ------------------------------------------
#
# test_handle_chunked_upload_invalid_upload_id_format: Check an attempt to
#    handle an upload fails if the provided ID doesn't meet the 22-char format.
#
# test_valid_patch_req_handled: Test that a PATCH request is handled
#    correctly and results in _handle_chunk_upload being called.
#
# test_valid_head_req_handled: Test that a HEAD request is handled
#    correctly and results in _handle_chunk_restart being called.
#
# test_post_req_err_without_file_id: Test that trying to call handle_upload
#    for a POST request without providing a file_id results in a 500 error.
#
# test_valid_post_req_handled: Test that a valid POST request is handled
#    correctly and results in calling _handle_new_chunk_upload
#
# test_invalid_method_error: Test that a call to handle_upload with an invalid
#    method returns a 405 - method not supported - error.
#
#
# TESTS FOR _handle_new_chunk_upload FUNCTION
# -------------------------------------------
#
# test_new_chunk_upload_invalid_file_value: Test that a request for a new
#    chunked upload without '{}' provided for the 'filepond' content in the
#    data results in a 400 bad request.
#
# test_new_chunk_upload_missing_len_header: Test that a new chunked upload
#    request that is missing the HTTP_UPLOAD_LENGTH fails with a 400 error.
#
# test_new_chunk_upload_dir_outside_storage_base: Test that we can't set up
#    a new chunked upload to use a directory outside the base storage location.
#
# test_new_chunk_upload_storage_dir_not_exists: Test that we get a 500 error
#    if the base storage location specified in the app config doesn't exist.
#
# test_new_chunk_upload_dir_exists: Test that we get a 500 error if the
#    upload directory for the temporary upload data files already exists.
#
# test_new_chunk_upload_successful: Test that a valid request for a new
#    chunked upload succeeds.
#
# TESTS FOR _handle_chunk_upload FUNCTION
# -------------------------------------------
#
# test_upload_chunk_missing_id: Test that a request to upload a chunk without
#    the required chunk ID fails with a 400 error.
#
# test_upload_chunk_invalid_id: Test that a request to upload a chunk with an
#    invalid chunk ID fails with a 400 error.
#
# test_upload_chunk_offset_missing: Test that a chunk upload request missing
#    the required HTTP_UPLOAD_OFFSET header parameter fails with a 400 error.
#
# test_upload_chunk_length_missing: Test that a chunk upload request missing
#    the required HTTP_UPLOAD_LENGTH header parameter fails with a 400 error.
#
# test_upload_chunk_name_missing: Test that a chunk upload request missing
#    the required HTTP_UPLOAD_NAME header parameter fails with a 400 error.
#
# test_upload_chunk_length_changed: Test that a 400 error is generated if the
#    specified upload length parameter doesn't match the original value
#    stored when the chunked upload was set up.
#
# test_upload_chunk_name_changed: Test that a 400 error is generated if the
#    specified upload name doesn't match the name stored with the first chunk.
#
# test_upload_chunk_offset_different: Test that a 400 error is raised if the
#    offset we have recorded is different to the one provided with the chunk.
#
# test_upload_chunk_invalid_data_type: Test that a 400 error is raised if the
#    uploaded data is not provided as a string or bytes.
#
# test_upload_chunk_dir_missing(self): Test that a 500 error is raised if the
#    upload directory for chunk storage is missing.
#
# test_upload_chunk_byte_data: Test that a 400 error is raised if the
#    uploaded data is not provided as a string or bytes.
#
# test_upload_chunk_string_data: Test that a 400 error is raised if the
#    uploaded data is not provided as a string or bytes.
#
# test_upload_chunk_name_set_chunk0: Test that when the first chunk is
#    uploaded, the file name is set on the TemporaryUploadChunked object.
#
# test_upload_chunk_upload_complete: Test that when the chunk being uploaded
#    is the final chunk, that there is an attempt to store the final data file.
#
# test_upload_chunk_upload_complete_set: Test that when the chunk being
#    uploaded has the final block of data, upload_complete is set.
#
# test_upload_empty_chunk_complete: Test that a request to upload a chunk with
#    no data, is successfully handled. When uploading a file that has a size
#    that is an exact multiple of the upload chunk size set on the
#    client-side, there will be a final PATCH request with no data.
#
# test_upload_empty_chunk_incomplete: Test that a request to upload a chunk
#    with no data, when the upload is not complete fails with a 400 error.
#
# test_store_upload_file_error_captured: Test that when _store_upload is
#    called within handle_chunk_upload, if a FileNotFoundError is raised
#    then this is captured a 500 error is returned.
#
# test_store_upload_value_error_captured: Test that when _store_upload is
#    called within handle_chunk_upload, if a ValueError is raised then
#    this is captured a 500 error is returned.
#
# TESTS FOR _store_upload FUNCTION
# --------------------------------
#
# test_store_upload_chunks_not_complete: Test that we get a ValueError if the
#    TemporaryUploadChunked obj for this call doesn't have upload_complete set.
#
# test_store_upload_chunk_missing: Test that a FileNotFoundError is raised if
#    a chunk file is missing.
#
# test_store_upload_stored_file_wrong_size: Test that if the final stored file
#    resulting from a chunked upload is of the wrong size, this is detected
#    and a ValueError is raised.
#
# test_store_upload_stored_file_missing: Test that if the final stored file is
#    not present after the final TemporaryUpload record has been saved that
#    a ValueError is raised.
#
# test_store_upload_successful: Test that _store_upload correctly handles a
#    valid set of chunks and creates a TemporaryUpload object.
#
# TESTS FOR _handle_chunk_restart FUNCTION
# ----------------------------------------
#
# test_chunk_restart_invalid_id: Test that attempt to restart a chunked upload
#    with an invalid upload_id results in a 404 since the upload isn't found.
#
# test_chunk_restart_completed_upload: Test that an attempt to restart a
#    completed chunked upload fails. The record should already have been
#    deleted but this case is checked for nonetheless.
#
# test_chunk_restart_data_dir_missing: Test that an attempt to restart a valid
#    upload generates a 500 error if the chunk file directory is not found.
#
# test_chunk_restart_successful: Test that a successful attempt to restart a
#    chunked upload results in a response with the upload_id and a 200 status.
#


class UploadersFileChunkedTestCase(TestCase):

    def setUp(self):
        self.upload_id = _get_file_id()
        self.file_id = _get_file_id()
        self.upload_name = 'my_test_file.png'
        self.uploader = FilepondChunkedFileUploader()
        self.request = MagicMock(spec=Request)
        self.request.META = {}
        self.request.user = AnonymousUser()
        self.request.data = ensure_text(
            'This is the test upload chunk data...')

    # Set up a TemporaryUploadChunked database object for use in the
    # _store_upload functions.
    def _setup_tuc(self, complete=False, last_chunk=3, offset=150000,
                   upload_name=None, total_size=1048576):
        if upload_name is None:
            upload_name = self.upload_name
        tuc = TemporaryUploadChunked(
            upload_id=self.upload_id, file_id=self.file_id,
            upload_name=upload_name, upload_dir=self.upload_id,
            offset=offset, last_chunk=last_chunk,
            total_size=total_size, upload_complete=complete)
        tuc.save()
        return tuc

    # TESTS FOR TOP-LEVEL handle_upload FUNCTION
    # ------------------------------------------
    def test_handle_chunked_upload_invalid_upload_id_format(self):
        r = self.uploader.handle_upload(self.request, 'fdsfdsfds')
        # Add parameters to the response so that it can be rendered
        r = prep_response(r)
        self.assertContains(r, 'Invalid ID for handling upload.',
                            status_code=500)

    def test_valid_patch_req_handled(self):
        self.request.method = 'PATCH'
        self.uploader._handle_chunk_upload = MagicMock()
        self.uploader.handle_upload(self.request, self.upload_id)
        self.uploader._handle_chunk_upload.assert_called_with(self.request,
                                                              self.upload_id)

    def test_valid_head_req_handled(self):
        self.request.method = 'HEAD'
        self.uploader._handle_chunk_restart = MagicMock()
        self.uploader.handle_upload(self.request, self.upload_id)
        self.uploader._handle_chunk_restart.assert_called_with(self.request,
                                                               self.upload_id)

    def test_post_req_err_without_file_id(self):
        self.request.method = 'POST'
        r = self.uploader.handle_upload(self.request, self.upload_id)
        r = prep_response(r)
        self.assertContains(r, 'Invalid ID for handling upload.',
                            status_code=500)

    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_handle_new_chunk_upload')
    def test_valid_post_req_handled(self, mock_hncu):
        self.request.method = 'POST'
        self.uploader.handle_upload(self.request, self.upload_id, self.file_id)
        mock_hncu.assert_called_with(self.request, self.upload_id,
                                     self.file_id)

    def test_invalid_method_error(self):
        '''Test that a call to handle_upload with an invalid method
           returns a 405 - method not supported - error.'''
        self.request.method = 'DELETE'
        self.request.data = _setupRequestData({'filepond': '{}'})
        r = self.uploader.handle_upload(self.request, self.upload_id,
                                        self.file_id)
        r = prep_response(r)
        self.assertContains(r, 'Invalid method.', status_code=405)

    # TESTS FOR _handle_new_chunk_upload FUNCTION
    # -------------------------------------------
    def test_new_chunk_upload_invalid_file_value(self):
        self.request.data = _setupRequestData({'filepond': 'Some data.'})
        r = self.uploader._handle_new_chunk_upload(
            self.request, self.upload_id, self.file_id)
        r = prep_response(r)
        self.assertContains(r,
                            ('An invalid file object has been received for a '
                             'new chunked upload request.'), status_code=400)

    def test_new_chunk_upload_missing_len_header(self):
        self.request.data = _setupRequestData({'filepond': '{}'})
        self.request.META = {}
        r = self.uploader._handle_new_chunk_upload(
            self.request, self.upload_id, self.file_id)
        r = prep_response(r)
        self.assertContains(r, 'No length for new chunked upload request.',
                            status_code=400)

    def test_new_chunk_upload_dir_outside_storage_base(self):
        self.request.data = _setupRequestData({'filepond': '{}'})
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}
        r = self.uploader._handle_new_chunk_upload(
            self.request, '../../%s' % self.upload_id, self.file_id)
        r = prep_response(r)
        self.assertContains(r, 'Unable to create storage for upload data.',
                            status_code=500)

    @patch('os.path.exists')
    def test_new_chunk_upload_base_storage_dir_not_exists(self, mock_ope):
        mock_ope.return_value = False

        self.request.data = _setupRequestData({'filepond': '{}'})
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}
        r = self.uploader._handle_new_chunk_upload(
            self.request, self.upload_id, self.file_id)
        r = prep_response(r)
        self.assertContains(r, 'Data storage error occurred.', status_code=500)

    @patch('os.path.exists')
    def test_new_chunk_upload_storage_dir_exists(self, mock_ope):
        mock_ope.return_value = True

        self.request.data = _setupRequestData({'filepond': '{}'})
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}

        with patch('os.makedirs') as mock_osmd:
            mock_osmd.side_effect = OSError('[Mock] Unable to create dir!')
            r = self.uploader._handle_new_chunk_upload(
                self.request, self.upload_id, self.file_id)

        r = prep_response(r)
        self.assertContains(r, 'Unable to prepare storage for upload data.',
                            status_code=500)

    @patch('os.path.exists')
    def test_new_chunk_upload_successful(self, mock_ope):
        mock_ope.return_value = True

        self.request.data = _setupRequestData({'filepond': '{}'})
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}

        with patch('os.makedirs'):
            r = self.uploader._handle_new_chunk_upload(
                self.request, self.upload_id, self.file_id)

        r = prep_response(r)
        self.assertContains(r, self.upload_id, status_code=200)

    # TESTS FOR _handle_chunk_upload FUNCTION
    # -------------------------------------------
    def test_upload_chunk_missing_id(self):
        res = self.uploader._handle_chunk_upload(self.request, '')
        res = prep_response(res)
        self.assertContains(res, 'A required chunk parameter is missing.',
                            status_code=400)

    def test_upload_chunk_invalid_id(self):
        res = self.uploader._handle_chunk_upload(self.request, 'asddad')
        res = prep_response(res)
        self.assertContains(res, 'Invalid chunk upload request data',
                            status_code=400)

    def test_upload_chunk_offset_missing(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Chunk upload is missing required metadata',
                            status_code=400)

    def test_upload_chunk_length_missing(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Chunk upload is missing required metadata',
                            status_code=400)

    def test_upload_chunk_name_missing(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size}
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Chunk upload is missing required metadata',
                            status_code=400)

    def test_upload_chunk_length_changed(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': 250000,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, ('ERROR: Upload metadata is invalid - size '
                                  'changed'), status_code=400)

    def test_upload_chunk_name_changed(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': 'different_name.png'}
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Chunk upload file metadata is invalid',
                            status_code=400)

    def test_upload_chunk_offset_different(self):
        tuc = self._setup_tuc(offset=100000)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'ERROR: Chunked upload metadata is invalid.',
                            status_code=400)

    def test_upload_chunk_invalid_data_type(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        self.request.data = object()
        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Upload data type not recognised.',
                            status_code=400)

    def test_upload_chunk_dir_missing(self):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        with patch('os.path.exists', return_value=False):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Chunk storage location error',
                            status_code=500)

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    def test_upload_chunk_byte_data(self, _):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        self.request.data = ensure_binary(
            'This is the test upload chunk data...')

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)
        res = prep_response(res)
        self.assertContains(res, self.upload_id, status_code=200)

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    def test_upload_chunk_string_data(self, _):
        tuc = self._setup_tuc()
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)
        res = prep_response(res)
        self.assertContains(res, self.upload_id, status_code=200)

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    def test_upload_chunk_name_set_chunk0(self, _):
        tuc = self._setup_tuc(last_chunk=0, upload_name='')
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': self.upload_name}

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)
        res = prep_response(res)
        self.assertContains(res, self.upload_id, status_code=200)
        new_tuc = TemporaryUploadChunked.objects.get(upload_id=self.upload_id)
        self.assertEqual(new_tuc.upload_name, self.upload_name,
                         'Upload name has not been set on first chunk upload.')

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_store_upload')
    def test_upload_chunk_upload_complete(self, mock_store_upload, _):
        tuc = self._setup_tuc(complete=True)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': tuc.total_size,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)
        res = prep_response(res)
        mock_store_upload.assert_called_once_with(tuc)
        self.assertContains(res, self.upload_id, status_code=200)

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_store_upload')
    def test_upload_chunk_upload_complete_set(self, mock_store_upload, _):
        tuc = self._setup_tuc(complete=False, total_size=150041)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': 150041,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        self.request.data = str('This is the final chunk of upload data...')

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)
        res = prep_response(res)
        mock_store_upload.assert_called_once_with(tuc)
        self.assertContains(res, self.upload_id, status_code=200)

    def test_upload_empty_chunk_complete(self):
        '''Test that a request to upload a chunk with no data, is successfully
           handled. When uploading a file that has a size that is an exact
           multiple of the upload chunk size set on the client-side, there
           will be a final PATCH request with no data.'''
        tuc = self._setup_tuc(complete=True, total_size=345644)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 345644,
                             'HTTP_UPLOAD_LENGTH': 345644,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        # When no data is available request.data is set to an empty dict
        self.request.data = {}

        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, self.upload_id, status_code=200)

    def test_upload_empty_chunk_incomplete(self):
        '''Test that a request to upload a chunk with no data, when the upload
           is not complete fails with a 400 error.'''
        tuc = self._setup_tuc(complete=True, total_size=345644)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 301732,
                             'HTTP_UPLOAD_LENGTH': 345644,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        # When no data is available request.data is set to an empty dict
        self.request.data = {}

        res = self.uploader._handle_chunk_upload(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Upload data type not recognised.',
                            status_code=400)

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_store_upload')
    def test_store_upload_file_error_captured(self, mock_store_upload, _):
        ''' Test that when _store_upload is called within handle_chunk_upload,
            if a FileNotFoundError is raised then this is captured a 500 error
            is returned.'''
        tuc = self._setup_tuc(complete=True, total_size=1048576)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': 1048576,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        self.request.data = str('This upload is complete...')

        mock_store_upload.side_effect = FileNotFoundError(
            'The file could not be found during store of upload.')

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)

        mock_store_upload.assert_called_once_with(tuc)
        res = prep_response(res)
        self.assertContains(res, 'Error storing uploaded file.',
                            status_code=500)

    @patch('django_drf_filepond.models.FilePondUploadSystemStorage.save')
    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_store_upload')
    def test_store_upload_value_error_captured(self, mock_store_upload, _):
        ''' Test that when _store_upload is called within handle_chunk_upload,
            if a ValueError is raised then this is captured a 500 error is
            returned.'''
        tuc = self._setup_tuc(complete=True, total_size=1048576)
        self.request.META = {'HTTP_UPLOAD_OFFSET': 150000,
                             'HTTP_UPLOAD_LENGTH': 1048576,
                             'HTTP_UPLOAD_NAME': tuc.upload_name}
        self.request.data = str('This upload is complete...')

        mock_store_upload.side_effect = ValueError(
            'ValueError when storing file.')

        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_upload(self.request,
                                                     self.upload_id)

        mock_store_upload.assert_called_once_with(tuc)
        res = prep_response(res)
        self.assertContains(res, 'Error storing uploaded file.',
                            status_code=500)

    # TESTS FOR _store_upload FUNCTION
    # --------------------------------
    def test_store_upload_chunks_not_complete(self):
        tuc = self._setup_tuc()
        with self.assertRaisesMessage(
                ValueError, ('Attempt to store an incomplete upload with ID '
                             '<%s>' % self.upload_id)):
            self.uploader._store_upload(tuc)

    # Test a case where the second upload chunk is missing.
    # We need to mock things so that the attempt to open the
    # first chunk works successfully...
    def test_store_upload_chunk_missing(self):
        tuc = self._setup_tuc(True)
        tuc.last_chunk = 3
        tuc.save()
        chunk_base = os.path.join(storage.base_location, tuc.upload_dir,
                                  '%s_' % (tuc.file_id))

        def mock_path_exists_se(chunk_file):
            if chunk_file == chunk_base + '2':
                return False
            return True

        def mock_open_se(chunk_file, _):
            data = BytesIO((os.path.basename(chunk_file) + '_*...*_').encode())
            setattr(data, 'mode', None)
            return data

        with patch('os.path.exists', side_effect=mock_path_exists_se):
            open_name = '%s.open' % django_drf_filepond.uploaders.__name__
            utils_open_name = '%s.open' % django_drf_filepond.utils.__name__
            with patch(open_name, side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    with patch('os.path.getsize', return_value=6):
                        with self.assertRaisesMessage(
                                FileNotFoundError,
                                'Chunk file not found for chunk <2>'):
                            self.uploader._store_upload(tuc)

    # We patch TemporaryUpload.save so that it doesn't try to save a file to
    # disk but also so that it doesn't call os.path.exists as part of the save
    # process since we patch os.path.exists later and this causes problems
    # with attempting to save the file anyway.
    @patch('django_drf_filepond.models.TemporaryUpload.save')
    def test_store_upload_stored_file_wrong_size(self, _):
        # Test a case where the second upload chunk is missing.
        tuc = self._setup_tuc(True)
        tuc.last_chunk = 3
        tuc.save()

        tuc.save = MagicMock()

        chunk_base = os.path.join(storage.base_location, tuc.upload_dir,
                                  tuc.file_id)

        def mock_path_exists_se(chunk_file):
            # Need to have something that checks for the structure of the file
            # name since os.path.exists is used when trying to save the
            # TemporaryUpload record and it goes into an infinite loop checking
            # possible file names if we simply force this to return true always
            if chunk_file.startswith(chunk_base):
                return True
            return False

        def mock_open_se(chunk_file, _):
            return BytesIO((os.path.basename(chunk_file) + '_*...*_').encode())

        with patch('os.path.exists', side_effect=mock_path_exists_se):
            open_name = '%s.open' % django_drf_filepond.uploaders.__name__
            utils_open_name = '%s.open' % django_drf_filepond.utils.__name__
            with patch(open_name, side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    with patch('django_drf_filepond.models.TemporaryUpload'):
                        with patch('os.path.getsize', return_value=128000):
                            with self.assertRaisesMessage(
                                    ValueError, 'Stored file size wrong or '
                                    'file not found.'):
                                self.uploader._store_upload(tuc)

    # See comment on test_store_upload_stored_file_wrong_size re this patch
    @patch('django_drf_filepond.models.TemporaryUpload.save')
    def test_store_upload_stored_file_missing(self, _):
        tuc = self._setup_tuc(True)
        tuc.last_chunk = 3
        tuc.save()

        tuc.save = MagicMock()
        tuc.delete = MagicMock()

        chunk_base = os.path.join(storage.base_location, tuc.upload_dir,
                                  tuc.file_id)

        def mock_path_exists_se(chunk_file):
            # Need to have something that checks for the structure of the file
            # name since os.path.exists is used when trying to save the
            # TemporaryUpload record and it goes into an infinite loop checking
            # possible file names if we simply force this to return true always
            if chunk_file.startswith(chunk_base + '_'):
                return True
            return False

        def mock_open_se(chunk_file, _):
            return BytesIO((os.path.basename(chunk_file) + '_*...*_').encode())

        with patch('os.path.exists', side_effect=mock_path_exists_se):
            open_name = '%s.open' % django_drf_filepond.uploaders.__name__
            utils_open_name = '%s.open' % django_drf_filepond.utils.__name__
            with patch(open_name, side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    with patch('os.path.getsize', return_value=tuc.total_size):
                        # This shouldn't be required if the error is raised
                        # but in case it isn't, this handles os.remove calls
                        # after the point where the error should occur
                        with patch('os.remove'):
                            with self.assertRaisesMessage(
                                    ValueError, ('Stored file size wrong or '
                                                 'file not found.')):
                                self.uploader._store_upload(tuc)

    # See comment for test_store_upload_stored_file_wrong_size re this patch
    @patch('django_drf_filepond.models.TemporaryUpload.save')
    def test_store_upload_successful(self, _):
        tuc = self._setup_tuc(True)
        tuc.last_chunk = 3
        tuc.save()

        tuc.save = MagicMock()
        tuc.delete = MagicMock()

        chunk_base = os.path.join(storage.base_location, tuc.upload_dir,
                                  tuc.file_id)

        def mock_path_exists_se(chunk_file):
            LOG.debug('Mock os.path.exists call for: <%s>' % chunk_file)
            # Need to have something that checks for the structure of the file
            # name since os.path.exists is used when trying to save the
            # TemporaryUpload record and it goes into an infinite loop checking
            # possible file names if we simply force this to return true always
            if chunk_file.startswith(chunk_base):
                return True
            return False

        def mock_open_se(chunk_file, _):
            return BytesIO((os.path.basename(chunk_file) + '_*...*_').encode())

        with patch('os.path.exists', side_effect=mock_path_exists_se):
            open_name = '%s.open' % django_drf_filepond.uploaders.__name__
            utils_open_name = '%s.open' % django_drf_filepond.utils.__name__
            with patch(open_name, side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    with patch('os.path.getsize', return_value=tuc.total_size):
                        with patch('os.remove') as mock_rm:
                            self.uploader._store_upload(tuc)
                            mock_rm.test_assert_has_calls([chunk_base + '_1',
                                                           chunk_base + '_2',
                                                           chunk_base + '_3'])
                            # assert_called_once raises an AttributeError in
                            # Py3.5, it seems it's not available so using
                            # the _with variant instead.
                            tuc.delete.assert_called_once_with()

    # TESTS FOR _handle_chunk_restart FUNCTION
    # ----------------------------------------
    def test_chunk_restart_invalid_id(self):
        self._setup_tuc()
        new_upload_id = _get_file_id()
        res = self.uploader._handle_chunk_restart(self.request, new_upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Invalid upload ID specified.',
                            status_code=404)

    def test_chunk_restart_completed_upload(self):
        self._setup_tuc(complete=True)
        res = self.uploader._handle_chunk_restart(self.request, self.upload_id)
        res = prep_response(res)
        self.assertContains(res, 'Invalid upload ID specified.',
                            status_code=400)

    def test_chunk_restart_data_dir_missing(self):
        tuc = self._setup_tuc()
        with patch('os.path.exists', return_value=False):
            res = self.uploader._handle_chunk_restart(self.request,
                                                      tuc.upload_id)
        res = prep_response(res)
        self.assertContains(res, ('Invalid upload location, can\'t continue '
                                  'upload.'), status_code=500)

    def test_chunk_restart_successful(self):
        tuc = self._setup_tuc()
        tuc.last_chunk = 2
        tuc.offset = 100000
        tuc.save()
        with patch('os.path.exists', return_value=True):
            res = self.uploader._handle_chunk_restart(self.request,
                                                      tuc.upload_id)
        res = prep_response(res)
        self.assertContains(res, self.upload_id, status_code=200)
        self.assertIn('Upload-Offset', res,
                      'Upload-Offset header is missing from response')
        self.assertEqual(int(res['Upload-Offset']), tuc.offset,
                         'Upload-Offset in response doesn\'t match tuc obj.')
