import logging
import six

from django.test import TestCase

from rest_framework.request import Request
from django_drf_filepond.uploaders import FilepondFileUploader,\
    FilepondChunkedFileUploader, FilepondStandardFileUploader
from rest_framework.exceptions import MethodNotAllowed, ParseError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django_drf_filepond.utils import _get_file_id
from tests.utils import _setupRequestData

# Python 2/3 support
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

LOG = logging.getLogger(__name__)
#
# This test class tests the functionality of the base FilepondFileUploader
# class in the uploaders module.
#
# It checks that the right type of uploader is returned in response to
# get_uploader calls and tests the class-level _get_file_obj function.
#
# test_get_file_obj_std_field_name: Test that we can access a file object in
#    a request using the standard upload parameter name.
#
# test_get_file_obj_custom_field_name: Test that we can access a file object
#    in a request using a custom upload field name.
#
# test_get_file_obj_std_field_name_missing: Test that an error is raised when
#    we try to access a file from a request where the standard field name is
#    expected but missing.
#
# test_get_file_obj_custom_field_name_missing: Test that an error is raised
#    when we try to access a file from a request where the specfied custom
#    field name is missing in the request.
#
# test_get_file_obj_custom_field_multiple_entries_error: Test that a Parse
#    Error is generated when we are passed data that includes more than two
#    values for the custom field name - we can only accept one or two items.
#
# test_get_uploader_patch_req: Test that a PATCH request results in a
#    FilepondChunkedFileUploader being returned.
#
# test_get_uploader_head_req: Test that a HEAD request results in a
#    FilepondChunkedFileUploader being returned.
#
# test_get_uploader_post_req_std: Test that a regular file upload POST request
#    results in a FilepondStandardFileUploader being returned.
#
# test_get_uploader_post_req_chunk: Test that a chunked upload POST request
#    results in a FilepondChunkedFileUploader being returned.
#
# test_handle_upload_invalid_method_error: Test that a call to handle_upload
#    with an invalid method returns a 405 - method not supported - error.
#
# test_get_uploader_get_req: Test that a get request results in an exception
#    since no uploader type currently supports get requests.
#
# test_upload_id_valid: Test the upload ID validator with a valid ID
#
# test_upload_id_invalid: Test the upload ID validator with an invalid ID
#
# test_upload_id_wrong_data_type: Test the upload ID validator with an ID of
#    the wrong data type (i.e. not a string)
#
# test_file_id_valid: Test the file ID validator with a valid ID
#
# test_file_id_invalid: Test the file ID validator with an invalid ID
#
# test_file_id_wrong_data_type: Test the file ID validator with an ID of the
#    wrong data type (i.e. not a string)
#


class UploadersBaseTestCase(TestCase):

    def setUp(self):
        self.request = MagicMock(spec=Request)

    def test_get_file_obj_std_field_name(self):
        # The data may be a byte array, a string ('{}') or an UploadedFile
        # object depending on what type of filepond request we're handling.
        # This doesn't actually matter in this and the subsequent get_file_obj
        # tests, this is just checking that the data is correctly extracted.
        self.request.data = _setupRequestData({'filepond': '{}'})
        data = FilepondFileUploader._get_file_obj(self.request)
        self.assertEqual(data, '{}', 'Data was not correctly extracted from '
                         'the request.')

    def test_get_file_obj_custom_field_name(self):
        self.request.data = _setupRequestData(
            {'fp_upload_field': 'somefield', 'somefield': ['{}']})
        data = FilepondFileUploader._get_file_obj(self.request)
        self.assertEqual(data, '{}', 'Data was not correctly extracted from '
                         'the request.')

    def test_get_file_obj_std_field_name_missing(self):
        self.request.data = _setupRequestData({'somefield': '{}'})
        with self.assertRaisesMessage(
                ParseError, 'Could not find upload_field_name in request '
                            'data.'):
            FilepondFileUploader._get_file_obj(self.request)

    def test_get_file_obj_custom_field_name_missing(self):
        self.request.data = _setupRequestData({'fp_upload_field': 'somefield',
                                               'a_field': '{}'})
        with self.assertRaisesMessage(
                ParseError, 'Could not find upload_field_name in request '
                            'data.'):
            FilepondFileUploader._get_file_obj(self.request)

    def test_get_file_obj_custom_field_multiple_entries_error(self):
        self.request.data = _setupRequestData(
            {'fp_upload_field': 'somefield',
             'somefield': ['{}', '{some data}', 'some other data']})
        with self.assertRaisesMessage(
                ParseError, 'Invalid number of fields in request data.'):
            FilepondFileUploader._get_file_obj(self.request)

    def test_get_uploader_patch_req(self):
        self.request.method = 'PATCH'
        uploader = FilepondFileUploader.get_uploader(self.request)
        self.assertIsInstance(uploader, FilepondChunkedFileUploader,
                              'Expected a FilepondChunkedFileUploader but '
                              'the returned uploader is of a different type.')

    def test_get_uploader_head_req(self):
        self.request.method = 'HEAD'
        uploader = FilepondFileUploader.get_uploader(self.request)
        self.assertIsInstance(uploader, FilepondChunkedFileUploader,
                              'Expected a FilepondChunkedFileUploader but '
                              'the returned uploader is of a different type.')

    def test_get_uploader_post_req_std(self):
        file_obj = MagicMock(spec=InMemoryUploadedFile)
        self.request.method = 'POST'
        self.request.data = _setupRequestData({'filepond': [{}, file_obj]})
        uploader = FilepondFileUploader.get_uploader(self.request)
        self.assertIsInstance(uploader, FilepondStandardFileUploader,
                              'Expected a FilepondStandardFileUploader but '
                              'the returned uploader is of a different type.')

    def test_get_uploader_post_req_chunk(self):
        self.request.method = 'POST'
        self.request.data = _setupRequestData({'filepond': '{}'})
        self.request.META = {'HTTP_UPLOAD_LENGTH': 1048576}
        uploader = FilepondFileUploader.get_uploader(self.request)
        self.assertIsInstance(uploader, FilepondChunkedFileUploader,
                              'Expected a FilepondChunkedFileUploader but '
                              'the returned uploader is of a different type.')

    def test_get_uploader_get_req(self):
        self.request.method = 'GET'
        with self.assertRaisesMessage(MethodNotAllowed,
                                      'GET is an invalid method type'):
            FilepondFileUploader.get_uploader(self.request)

    def test_upload_id_valid(self):
        # _get_file_id is currently used for getting both file+upload IDs
        # since the spec for both is the same at present.
        upload_id = _get_file_id()
        self.assertTrue(
            FilepondFileUploader._upload_id_valid(upload_id),
            'A valid upload ID has been provided and this test should pass!')

    def test_upload_id_invalid(self):
        upload_id = 'sadadadasd'
        self.assertFalse(
            FilepondFileUploader._upload_id_valid(upload_id),
            'Invalid upload ID (wrong length) provided. Failure expected.')

    def test_upload_id_wrong_data_type(self):
        # _get_file_id is currently used for getting both file+upload IDs
        # since the spec for both is the same at present. Test using bytes
        # instead of str
        upload_id = _get_file_id().encode()
        self.assertFalse(
            FilepondFileUploader._upload_id_valid(upload_id),
            ('The provided upload ID is of the wrong data type, this test '
             'should fail.'))

    def test_file_id_valid(self):
        file_id = _get_file_id()
        self.assertTrue(
            FilepondFileUploader._file_id_valid(file_id),
            'A valid file ID has been provided and this test should pass!')

    def test_file_id_invalid(self):
        file_id = 'sadadadasd'
        self.assertFalse(
            FilepondFileUploader._file_id_valid(file_id),
            'Invalid file ID (wrong length) provided. Failure expected.')

    def test_file_id_wrong_data_type(self):
        # Test using bytes instead of str
        file_id = six.ensure_binary(_get_file_id())
        self.assertFalse(
            FilepondFileUploader._file_id_valid(file_id),
            ('The provided file ID is of the wrong data type, this test '
             'should fail.'))
