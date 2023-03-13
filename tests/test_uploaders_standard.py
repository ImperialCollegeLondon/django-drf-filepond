import logging

from django.test import TestCase

from rest_framework.request import Request
from django_drf_filepond.uploaders import FilepondStandardFileUploader
from rest_framework.exceptions import ParseError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django_drf_filepond.utils import _get_file_id
from django.contrib.auth.models import AnonymousUser
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond.renderers import PlainTextRenderer
from tests.utils import _setupRequestData

# Python 2/3 support
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

LOG = logging.getLogger(__name__)
#
# This test class tests the functionality of the FilepondStandardFileUploader
# class in the uploaders module. This class handles uploads of files that are
# not chunked and are received in a single block.
#
# test_handle_valid_file_upload: Check that when we call handle_upload with
#    a valid set of parameters, the file is stored as a TemporaryUpload and
#    we get a response back with the upload_id that we can use to verify
#    that the TemporaryUpload has been stored.
#
# test_handle_file_upload_invalid_upload_id: Check that when we call
#    handle_upload with an invalid upload_id (one that doesn't meet the spec
#    of being 22 characters in length) that we get an error generated.
#
# test_handle_file_upload_invalid_file_id: Check that when we call
#    handle_upload with an invalid upload_id (one that doesn't meet the spec
#    of being 22 characters in length) that we get an error generated.
#
# test_handle_file_upload_invalid_file_obj: Check that we get an error when
#    we try to call handle_upload with a request that doesn't contain a valid
#    FileUpload object.
#
# test_handle_file_upload_mising_file_obj: Check that we get an error when
#    we try to call handle_upload with a request that doesn't contain the
#    required key for the file upload data/object (raised from _get_file_obj)
#


class UploadersFileStandardTestCase(TestCase):

    def setUp(self):
        self.file_id = _get_file_id()
        self.upload_id = _get_file_id()
        self.file_name = 'my_uploaded_file.txt'
        self.request = MagicMock(spec=Request)
        self.request.user = AnonymousUser()
        file_obj = MagicMock(spec=InMemoryUploadedFile)
        file_obj.name = self.file_name
        self.request.data = _setupRequestData({'filepond': ['{}', file_obj]})
        self.uploader = FilepondStandardFileUploader()

    def test_handle_valid_file_upload(self):
        r = self.uploader.handle_upload(self.request, self.upload_id,
                                        self.file_id)
        self.assertEqual(r.status_code, 200, 'Response status code is invalid')

        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        fileid = tu.file_id
        uploadname = tu.upload_name
        tu.delete()

        self.assertEqual(r.data, self.upload_id, 'Response data is invalid')
        self.assertEqual(fileid, self.file_id,
                         'The TemporaryUpload stored file_id is not correct.')
        self.assertEqual(uploadname, self.file_name,
                         'The TemporaryUpload upload_name is not correct.')

    def test_handle_file_upload_invalid_upload_id(self):
        r = self.uploader.handle_upload(self.request, 'dfsdfsd', self.file_id)
        # Add relevant properties to the response so it can be rendered.
        r.accepted_renderer = PlainTextRenderer()
        r.accepted_media_type = 'text/plain'
        r.renderer_context = {}
        self.assertContains(r, 'Invalid ID for handling upload.',
                            status_code=500)

    def test_handle_file_upload_invalid_file_id(self):
        r = self.uploader.handle_upload(self.request, self.upload_id, 'dfsdfs')
        # Add relevant properties to the response so it can be rendered.
        r.accepted_renderer = PlainTextRenderer()
        r.accepted_media_type = 'text/plain'
        r.renderer_context = {}
        self.assertContains(r, 'Invalid ID for handling upload.',
                            status_code=500)

    def test_handle_file_upload_invalid_file_obj(self):
        self.request.data = _setupRequestData(
            {'filepond': ['{}', 'This is a test'.encode()]})
        # When run through DRF, the ParseError raised by handle_upload would
        # be captured and converted into a 400 response. Here we have to
        # capture the ParseError directly to check that this is working.
        with self.assertRaisesMessage(
                ParseError, 'Invalid data type has been parsed.'):
            self.uploader.handle_upload(self.request, self.upload_id,
                                        self.file_id)

    def test_handle_file_upload_mising_file_obj(self):
        self.request.data = _setupRequestData(
            {'notfilepond': ['{}', 'This is a test'.encode()]})
        # When run through DRF, the ParseError raised by handle_upload would
        # be captured and converted into a 400 response. Here we have to
        # capture the ParseError directly to check that this is working.
        with self.assertRaisesMessage(ParseError, 'Could not find '
                                      'upload_field_name in request data.'):
            self.uploader.handle_upload(self.request, self.upload_id,
                                        self.file_id)
