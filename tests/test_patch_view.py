import logging

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

from django_drf_filepond.utils import _get_file_id

# Python 2/3 support
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

LOG = logging.getLogger(__name__)
#
# Tests for checking the correct handling of incoming PATCH requests for
# individual file chunks of a chunked upload.
#
# test_patch_invalid_request_content_type: Try making a patch request with
#    an invalid content type and ensure that this is rejected. The content
#    type of patch requests, as set out in filepond's chunked upload info
#    in the documentation
#    (https://pqina.nl/filepond/docs/patterns/api/server/#process-chunks)
#    should be "application/offset+octet-stream"
#
# test_patch_valid_request: Test that a valid PATCH request results in
#    _handle_chunk_upload being called on the FilepondChunkedFileUploader
#
# test_head_request_valid: Test that a valid HEAD request results in a call
#    to _handle_chunk_restart.
#
# test_head_invalid_id: Test that an error is generated if we make a HEAD
#    request to continue an upload with an invalid ID. In this case invalid
#    means that the ID conforms to the 22-character spec but it is unknown.
#


class ProcessTestCase(TestCase):

    def setUp(self):
        pass

    def test_patch_invalid_request_content_type(self):
        chunk_id = _get_file_id()
        req_url = reverse('patch', args=[chunk_id])
        LOG.debug('About to run patch test with req_url: %s' % req_url)
        response = self.client.patch(req_url, data='Some byte data'.encode(),
                                     content_type='image/png')
        self.assertContains(response, 'Unsupported media type',
                            status_code=415)

    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_handle_chunk_upload')
    def test_patch_valid_request(self, mock_hcu):
        chunk_id = _get_file_id()
        req_url = reverse('patch', args=[chunk_id])
        LOG.debug('About to run patch test with req_url: %s' % req_url)
        mock_hcu.return_value = Response(chunk_id, status=status.HTTP_200_OK,
                                         content_type='text/plain')
        response = self.client.patch(
            req_url, data='Some byte data'.encode(),
            content_type='application/offset+octet-stream')
        self.assertContains(response, chunk_id, status_code=200)

    @patch('django_drf_filepond.uploaders.FilepondChunkedFileUploader.'
           '_handle_chunk_restart')
    def test_head_request_valid(self, mock_hcr):
        upload_id = _get_file_id()
        req_url = reverse('patch', args=[upload_id])
        mock_hcr.return_value = Response(
            upload_id, status=status.HTTP_200_OK,
            headers={'Upload-Offset': '100000'},
            content_type='text/plain')
        response = self.client.head(req_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.has_header('Upload-Offset'),
            'Offset header is missing from chunk restart response.')
        self.assertEqual(response['Upload-Offset'], '100000',
                         'Upload-Offset header has wrong value in response.')

    def test_head_invalid_id(self):
        upload_id = 'ababababababababababab'
        req_url = reverse('patch', args=[upload_id])
        response = self.client.head(req_url)
        self.assertEqual(response.data, 'Invalid upload ID specified.')
        self.assertEqual(response.status_code, 404)
