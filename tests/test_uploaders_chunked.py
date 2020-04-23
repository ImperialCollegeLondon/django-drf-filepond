import logging

from django.test import TestCase

from rest_framework.request import Request
from django_drf_filepond.uploaders import FilepondChunkedFileUploader
from django_drf_filepond.views import _get_file_id
from django.contrib.auth.models import AnonymousUser
from django_drf_filepond.renderers import PlainTextRenderer

# Python 2/3 support
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

# Python 2/3 support
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

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
# test_upload_chunk_byte_data: Test that a 400 error is raised if the
#    uploaded data is not provided as a string or bytes.
#
# test_upload_chunk_string_data: Test that a 400 error is raised if the
#    uploaded data is not provided as a string or bytes.

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
# test_store_upload_successful: Test that _store_upload correctly handles a
#    valid set of chunks and creates a TemporaryUpload object.
#
# TESTS FOR _handle_chunk_restart FUNCTION
# ----------------------------------------
#
# test_chunk_restart_invalid_id: Test that attempt to restart a chunked upload
#    with an invalid upload_id results in a 404 since the upload isn't found.
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
        self.uploader = FilepondChunkedFileUploader()
        self.request = MagicMock(spec=Request)
        self.request.user = AnonymousUser()

    # Since we're working with mocked requests that haven't been processed via
    # a DRF/Django view, the request won't reneder correctly without having
    # some parameters set. Using assertContains requires that the request has
    # these parameters set so this helper function is used to avoid repetition.
    def _prep_request(self, request):
        request.accepted_renderer = PlainTextRenderer()
        request.accepted_media_type = 'text/plain'
        request.renderer_context = {}
        return request

    # TESTS FOR TOP-LEVEL handle_upload FUNCTION
    # ------------------------------------------
    def test_handle_chunked_upload_invalid_upload_id_format(self):
        r = self.uploader.handle_upload(self.request, 'fdsfdsfds')
        # Add parameters to the response so that it can be rendered
        r = self._prep_request(r)
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
        r = self._prep_request(r)
        self.assertContains(r, 'Invalid ID for handling upload.',
                            status_code=500)

    def test_valid_post_req_handled(self):
        self.request.method = 'POST'
        self.uploader._handle_new_chunk_upload = MagicMock()
        self.uploader.handle_upload(self.request, self.upload_id, self.file_id)
        self.uploader._handle_new_chunk_upload.assert_called_with(
            self.request, self.upload_id, self.file_id)

    # TESTS FOR _handle_new_chunk_upload FUNCTION
    # -------------------------------------------
    def test_new_chunk_upload_invalid_file_value(self):
        self.request.data = {'filepond': 'Some data.'}
        r = self.uploader._handle_new_chunk_upload(
            self.request, self.upload_id, self.file_id)
        r = self._prep_request(r)
        self.assertContains(r,
                            ('An invalid file object has been received for a '
                             'new chunked upload request.'), status_code=400)

    def test_new_chunk_upload_missing_len_header(self):
        self.request.data = {'filepond': '{}'}
        self.request.META = {}
        r = self.uploader._handle_new_chunk_upload(
            self.request, self.upload_id, self.file_id)
        r = self._prep_request(r)
        self.assertContains(r, 'No length for new chunked upload request.',
                            status_code=400)

    def test_new_chunk_upload_dir_outside_storage_base(self):
        self.request.data = {'filepond': '{}'}
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}
        r = self.uploader._handle_new_chunk_upload(
            self.request, '../../%s' % self.upload_id, self.file_id)
        r = self._prep_request(r)
        self.assertContains(r, 'Unable to create storage for upload data.',
                            status_code=500)

    @patch('os.path.exists')
    def test_new_chunk_upload_storage_dir_not_exists(self, mock_ope):
        mock_ope.return_value = False
        self.request.data = {'filepond': '{}'}
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}
        r = self.uploader._handle_new_chunk_upload(
            self.request, self.upload_id, self.file_id)
        r = self._prep_request(r)
        self.assertContains(r, 'Data storage error occurred.', status_code=500)

    def test_new_chunk_upload_dir_exists(self):
        raise NotImplementedError()

    def test_new_chunk_upload_successful(self):
        raise NotImplementedError()

    # TESTS FOR _handle_chunk_upload FUNCTION
    # -------------------------------------------
    def test_upload_chunk_missing_id(self):
        raise NotImplementedError()

    def test_upload_chunk_invalid_id(self):
        raise NotImplementedError()

    def test_upload_chunk_offset_missing(self):
        raise NotImplementedError()

    def test_upload_chunk_length_missing(self):
        raise NotImplementedError()

    def test_upload_chunk_name_missing(self):
        raise NotImplementedError()

    def test_upload_chunk_length_changed(self):
        raise NotImplementedError()

    def test_upload_chunk_name_changed(self):
        raise NotImplementedError()

    def test_upload_chunk_offset_different(self):
        raise NotImplementedError()

    def test_upload_chunk_invalid_data_type(self):
        raise NotImplementedError()

    def test_upload_chunk_byte_data(self):
        raise NotImplementedError()

    def test_upload_chunk_string_data(self):
        raise NotImplementedError()

    # TESTS FOR _store_upload FUNCTION
    # --------------------------------
    def test_store_upload_chunks_not_complete(self):
        raise NotImplementedError()

    def test_store_upload_chunk_missing(self):
        raise NotImplementedError()

    def test_store_upload_stored_file_wrong_size(self):
        raise NotImplementedError()

    def test_store_upload_successful(self):
        raise NotImplementedError()

    # TESTS FOR _handle_chunk_restart FUNCTION
    # ----------------------------------------
    def test_chunk_restart_invalid_id(self):
        raise NotImplementedError()

    def test_chunk_restart_data_dir_missing(self):
        raise NotImplementedError()

    def test_chunk_restart_successful(self):
        raise NotImplementedError()
