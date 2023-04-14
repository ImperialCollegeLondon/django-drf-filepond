import logging
import os
# Switched to using Message rather than cgi.parse_header for parsing and
# checking header params since cgi is deprecated and will be removed in py3.13
from email.message import Message

import httpretty
import requests
from django.test.testcases import TestCase
from django.urls import reverse
from django_drf_filepond import drf_filepond_settings
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond.views import FetchView
from httpretty import register_uri
from requests.exceptions import ConnectionError
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

# Python 2/3 support
try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

LOG = logging.getLogger(__name__)


#########################################################################
# The fetch endpoint is used when a link for a remote file is provided
# to filepond. https://pqina.nl/filepond/docs/patterns/api/server/#fetch
# The filepond client makes a fetch request to the server which proxies
# the request for the remote file (avoiding CORS issues) and then returns
# the file to the client. With the most recent update to filepond, there
# is an option to send a fetch HEAD request which proxies the request to
# download the file at the target URL but then stores the file on the
# server as though it had been uploaded from filepond. The server
# returns headers to the client with file metadata so that the client UI
# can be updated with the file data.
#
# test_fetch_incorrect_param: Make a GET request to the fetch endpoint
#     with an incorrect query string parameter key
#
# test_fetch_invalid_url: Make a GET request to the fetch endpoint with
#     the target parameter containing an invalid (incorrect format) URL.
#
# test_fetch_head_connection_error: Make a GET request to the fetch
#     endpoint with a target file URL that can't be accessed and results
#     in a connection error.
#
# test_fetch_file_notfound_error: Make a GET request to the fetch
#     endpoint with a target file URL that can't be found (results in 404)
#
# test_fetch_http_response_not_allowed: Make a GET request to the fetch
#     endpoint with a target file URL that results in return of an HTML
#     file. At present, django-drf-filepond flags this as an error since
#     it may be the result of an error information page being displayed.
#
# test_fetch_with_filename: Make a GET request to the fetch endpoint with
#     the target set to be a named file. Ensure that the expected file
#     content is returned and the file name is in the Content-Disposition
#     header.
#
# test_fetch_without_filename: Make a GET request to the fetch endpoint
#     with the target set to be a URL without a filename at the end.
#     Ensure that the Content-Disposition header contains an
#     auto-generated 22-character file name.
#
# test_fetch_head_with_filename: Make a HEAD request to the fetch
#     endpoint to get the named file at the remote URL and ensure that we
#     get back headers containing the file metadata while the file is
#     downloaded and stored by the server.
#
# test_fetch_head_without_filename: Make a HEAD request to the fetch
#     endpoint to get the file at the remote URL and ensure that we
#     get back headers containing the file metadata, including an auto-
#     generated 22-character filename, and that the file is stored on the
#     server.
#
# test_fetch_process_req_filename_from_contentdisposition: Test the fetch
#    class's _process_request function to ensure that a filename stored in
#    a response's Content-Disposition header is correctly used.
#
# test_fetch_process_req_connection_error_get: Check that a connection error
#    is correctly handled when requests.get is called in _process_request.
#    In theory, this shouldn't occur since requests.head is called first and
#    it's difficult to see where head may succeed and get fail straight after
#    but testing this case for completeness.
#
# test_fetch_head_response_object_returned: When fetch receives a HEAD
#    request, if _process_request returns a response object (in the case of
#    an error occurring), test that this is correctly returned without
#    further post-processing.
#
# test_fetch_head_response_unexpected_return_type: When fetch receives a
#    HEAD request, it calls _process_request and expects a tuple or Response
#    object back. Check that an unexpected response type is handled and
#    results in a ValueError.
#
# test_fetch_get_response_object_returned: When fetch receives a GET request,
#    if _process_request returns a response object (in the case of an error
#    occurring), test that this is correctly returned without further
#    post-processing.
#
# test_fetch_get_response_unexpected_return_type: When fetch receives a GET
#    request, it calls _process_request and expects a tuple or Response
#    object back. Check that an unexpected response type is handled and
#    results in a ValueError.
#
# test_fetch_binary_jpeg: When fetch receives a GET request for any type of
#    data, the response should be passed through without any issue. When
#    requesting binary data such as a JPEG image file, this was causing an
#    issue as described in #23. This test checks binary data is handled OK.
#
class FetchTestCase(TestCase):

    def test_fetch_incorrect_param(self):
        response = self.client.get((reverse('fetch') +
                                    '?somekey=http://localhost/test'))
        self.assertContains(response,
                            'Required query parameter(s) missing.',
                            status_code=400)

    def test_fetch_invalid_url(self):
        test_url = 'htt://localhost23/test'
        response = self.client.get((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        self.assertContains(
            response, 'An invalid URL <%s> has been provided' % test_url,
            status_code=400)

    @httpretty.activate
    def test_fetch_head_connection_error(self):
        test_url = 'http://localhost/test.txt'

        def connection_error_callback(request, uri, response_headers):
            raise requests.exceptions.ConnectionError('Connection error.')

        register_uri(method=httpretty.HEAD,
                     uri=test_url,
                     status=200,
                     body=connection_error_callback)

        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.get('http://localhost' + (reverse('fetch') +
                         ('?target=%s' % test_url)))

    @httpretty.activate
    def test_fetch_file_notfound_error(self):
        test_url = 'http://localhost/test.txt'

        register_uri(method=httpretty.HEAD,
                     uri=test_url,
                     status=404)

        response = self.client.get((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        self.assertContains(
            response,
            'The remote file was not found.', status_code=404)

    @httpretty.activate
    def test_fetch_http_response_not_allowed(self):
        test_url = 'http://localhost/test.txt'

        def response_callback(request, uri, response_headers):
            response_headers.update({'Content-Type': 'text/html'})
            return [200, response_headers, '<html><body></body></html>']

        register_uri(method=httpretty.HEAD,
                     uri=test_url,
                     status=200,
                     body=response_callback)

        response = self.client.get((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        self.assertContains(response, 'Provided URL links to HTML content.',
                            status_code=400)

    @httpretty.activate
    def _filename_fetch_test(self, test_url, test_content):

        def response_callback_head(request, uri, response_headers):
            response_headers.update({'Content-Type': 'text/plain'})
            return [200, response_headers, '']

        def response_callback_get(request, uri, response_headers):
            response_headers.update({'Content-Type': 'text/plain'})
            return [200, response_headers, test_content]

        register_uri(method=httpretty.HEAD,
                     uri=test_url,
                     status=200,
                     body=response_callback_head)
        register_uri(method=httpretty.GET,
                     uri=test_url,
                     status=200,
                     body=response_callback_get)

        response = self.client.get((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        return response

    @httpretty.activate
    def _filename_fetch_head_test(self, test_url, test_content):

        def response_callback_head(request, uri, response_headers):
            response_headers.update({'Content-Type': 'text/plain'})
            return [200, response_headers, '']

        def response_callback_get(request, uri, response_headers):
            response_headers.update({'Content-Type': 'text/plain'})
            return [200, response_headers, test_content]

        register_uri(method=httpretty.HEAD,
                     uri=test_url,
                     status=200,
                     body=response_callback_head)
        register_uri(method=httpretty.GET,
                     uri=test_url,
                     status=200,
                     body=response_callback_get)

        response = self.client.head((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        return response

    @httpretty.activate
    def test_fetch_with_filename(self):
        filename = 'test.txt'
        test_url = 'http://localhost/%s' % filename
        test_content = '*This is the file content!*'

        response = self._filename_fetch_test(test_url, test_content)

        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))
        msg = Message()
        msg['content-type'] = response['Content-Disposition']
        self.assertTrue(
            msg.get_param('filename'),
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        # fname = cdisp[1]['filename']
        fname = msg.get_param('filename')

        self.assertContains(response, '*This is the file content!*',
                            status_code=200)
        self.assertEqual(
            filename, fname,
            'Returned filename is not equal to the provided filename value.')

    @httpretty.activate
    def test_fetch_without_filename(self):
        test_url = 'http://localhost/getfile/'
        test_content = '*This is the file content!*'

        response = self._filename_fetch_test(test_url, test_content)

        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))
        
        msg = Message()
        msg['content-type'] = response['Content-Disposition']
        self.assertTrue(
            msg.get_param('filename'),
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        fname = msg.get_param('filename')

        self.assertContains(response, '*This is the file content!*',
                            status_code=200)
        LOG.debug('Returned filename is <%s>' % fname)
        self.assertEqual(
            len(fname), 22,
            'Returned filename is not a 22 character auto-generated name.')

    def test_fetch_head_with_filename(self):
        tmp_upload_dir = drf_filepond_settings.UPLOAD_TMP
        self.uploaddir_exists_pre_test = os.path.exists(tmp_upload_dir)

        filename = 'test2.txt'
        test_url = 'http://localhost/%s' % filename
        test_content = '*This is the file number 2 content!*'

        response = self._filename_fetch_head_test(test_url, test_content)

        # https://pqina.nl/filepond/docs/patterns/api/server/#fetch shows
        # the headers that we should be expecting the server to return
        # Content-Disposition, Content-Length, X-Content-Transfer-Id
        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))

        msg = Message()
        msg['content-type'] = response['Content-Disposition']
        self.assertTrue(
            msg.get_param('filename'),
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        fname = msg.get_param('filename')

        self.assertEqual(
            filename, fname,
            'Returned filename is not equal to the provided filename value.')
        self.assertEqual(int(response['Content-Length']),
                         len(test_content),
                         ('Returned content length <%s> is not equal to '
                          'data length <%s>.') %
                         (response['Content-Length'], len(test_content)))
        transfer_id = response['X-Content-Transfer-Id']
        self.assertEqual(len(transfer_id), 22,
                         ('Returned filename is not a 22 character '
                          'auto-generated name.'))

        # Check that we have the data for the stored in the database then
        # remove created file and dir
        tu = TemporaryUpload.objects.get(upload_id=transfer_id)
        dir_path = os.path.join(tmp_upload_dir, transfer_id)
        file_path = os.path.join(dir_path, os.path.basename(tu.file.path))
        dir_list = os.listdir(dir_path)
        if (len(transfer_id) == 22 and os.path.exists(file_path) and
                len(dir_list) == 1):
            LOG.debug('Removing generated file <%s>' % file_path)
            os.remove(file_path)
            LOG.debug('Removing temporary directory <%s>' % dir_path)
            os.rmdir(dir_path)
        else:
            LOG.error('Couldn\'t proceed with file deleting since the '
                      'response received was not the right length (22) '
                      'or the required directory doesn\'t exist')

    def test_fetch_head_without_filename(self):
        tmp_upload_dir = drf_filepond_settings.UPLOAD_TMP
        self.uploaddir_exists_pre_test = os.path.exists(tmp_upload_dir)

        test_url = 'http://localhost/getfile2/'
        test_content = '*This is the file number 2 content!*'

        response = self._filename_fetch_head_test(test_url, test_content)

        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))

        msg = Message()
        msg['content-type'] = response['Content-Disposition']
        self.assertTrue(
            msg.get_param('filename'),
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        fname = msg.get_param('filename')
        
        self.assertEqual(
            len(fname), 22,
            'Returned filename is not a 22 character auto-generated name.')
        self.assertEqual(int(response['Content-Length']),
                         len(test_content),
                         ('Returned content length <%s> is not equal to '
                          'data length <%s>.') %
                         (response['Content-Length'], len(test_content)))
        transfer_id = response['X-Content-Transfer-Id']
        self.assertEqual(len(response['X-Content-Transfer-Id']), 22,
                         ('Returned filename is not a 22 character '
                          'auto-generated name.'))

        # Check that we have the data for the stored in the database then
        # remove created file and dir
        tu = TemporaryUpload.objects.get(upload_id=transfer_id)
        dir_path = os.path.join(tmp_upload_dir, transfer_id)
        file_path = os.path.join(dir_path, os.path.basename(tu.file.path))
        dir_list = os.listdir(dir_path)
        if (len(transfer_id) == 22 and os.path.exists(file_path) and
                len(dir_list) == 1):
            LOG.debug('Removing generated file <%s>' % file_path)
            os.remove(file_path)
            LOG.debug('Removing temporary directory <%s>' % dir_path)
            os.rmdir(dir_path)
        else:
            LOG.error('Couldn\'t proceed with file deleting since the '
                      'response received was not the right length (22) '
                      'or the required directory doesn\'t exist')

    def test_fetch_process_req_filename_from_contentdisposition(self):
        patcher_head = patch('requests.head')
        patcher_get = patch('requests.get')
        patcher_head.start()
        patcher_get.start()
        self.addCleanup(patcher_head.stop)
        self.addCleanup(patcher_get.stop)
        requests.get.return_value.__enter__.return_value.headers = {
            'Content-Disposition': 'filename=cd_test_file.txt'
        }
        (requests.get.return_value.__enter__.return_value.
            iter_content.return_value) = [b'Some test file content...']
        mock_head_resp = MagicMock()
        mock_head_resp.headers = {'Content-Type': 'text/plain'}
        mock_head_resp.status_code = 200
        requests.head.return_value = mock_head_resp
        mock_req = MagicMock()
        mock_req.query_params = {'target': 'http://localhost/test'}
        fv = FetchView()
        result = fv._process_request(mock_req)
        self.assertTrue((type(result) == tuple) and (len(result) == 4),
                        'The return type was not a tuple of the right length!')
        self.assertTrue(
            result[2] == 'cd_test_file.txt',
            ('File name cd_test_file.txt was not correctly extracted from '
             'the request, got [%s]' % result[2]))

    def test_fetch_process_req_connection_error_get(self):
        patcher_head = patch('requests.head')
        patcher_get = patch('requests.get')
        patcher_head.start()
        patcher_get.start()
        self.addCleanup(patcher_head.stop)
        self.addCleanup(patcher_get.stop)
        mock_head_resp = MagicMock()
        mock_head_resp.headers = {'Content-Type': 'text/plain'}
        mock_head_resp.status_code = 200
        requests.head.return_value = mock_head_resp
        requests.get.side_effect = ConnectionError('test_file')
        mock_req = MagicMock()
        mock_req.query_params = {'target': 'http://localhost/test'}
        fv = FetchView()
        with self.assertRaisesMessage(
                NotFound,
                'Unable to access the requested remote file: test_file'):
            fv._process_request(mock_req)

    def test_fetch_head_response_object_returned(self):
        patcher = patch('django_drf_filepond.views.FetchView._process_request')
        patcher.start()
        self.addCleanup(patcher.stop)
        FetchView._process_request.return_value = Response(data='test data')
        response = self.client.head((reverse('fetch') +
                                    ('?target=/test_target')))
        self.assertEqual(response.data, 'test data', 'Fetch HEAD has not '
                         'returned the expected response object.')

    def test_fetch_head_response_unexpected_return_type(self):
        patcher = patch('django_drf_filepond.views.FetchView._process_request')
        patcher.start()
        self.addCleanup(patcher.stop)
        FetchView._process_request.return_value = {}
        with self.assertRaisesMessage(
                ValueError,
                'process_request result is of an unexpected type'):
            self.client.head((reverse('fetch') + ('?target=/test_target')))

    def test_fetch_get_response_object_returned(self):
        patcher = patch('django_drf_filepond.views.FetchView._process_request')
        patcher.start()
        self.addCleanup(patcher.stop)
        FetchView._process_request.return_value = Response(data='test data')
        response = self.client.get((reverse('fetch') +
                                    ('?target=/test_target')))
        self.assertEqual(response.data, 'test data', 'Fetch GET has not '
                         'returned the expected response object.')

    def test_fetch_get_response_unexpected_return_type(self):
        patcher = patch('django_drf_filepond.views.FetchView._process_request')
        patcher.start()
        self.addCleanup(patcher.stop)
        FetchView._process_request.return_value = {}
        with self.assertRaisesMessage(
                ValueError,
                'process_request result is of an unexpected type'):
            self.client.get((reverse('fetch') + ('?target=/test_target')))

    @httpretty.activate
    def test_fetch_binary_jpeg(self):
        test_url = 'http://localhost/test_image.jpg'
        test_image = os.path.join(os.path.dirname(__file__), 'test_image.jpg')
        with open(test_image, 'rb') as f:
            test_image_data = f.read()

        def response_callback(request, uri, response_headers):
            response_headers.update({'Content-Type': 'image/jpeg'})
            if request.method == 'HEAD':
                return [200, response_headers, b'']
            else:
                return [200, response_headers, test_image_data]

        register_uri(method=httpretty.HEAD,
                     uri=test_url,
                     status=200,
                     body=response_callback)

        register_uri(method=httpretty.GET,
                     uri=test_url,
                     status=200,
                     body=response_callback)

        response = self.client.get((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        self.assertEqual(response.status_code, 200,
                         'Expected a 200 response code.')
