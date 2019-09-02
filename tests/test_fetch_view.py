import logging

from django.test.testcases import TestCase
from django.urls import reverse
from httpretty import register_uri
import httpretty
import requests
import cgi
import os

from django_drf_filepond import drf_filepond_settings
from django_drf_filepond.models import TemporaryUpload

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

        response = self.client.get((reverse('fetch') +
                                    ('?target=%s' % test_url)))
        self.assertContains(
            response,
            'Unable to access the requested remote file headers',
            status_code=500)

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
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue(
            'filename' in cdisp[1],
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        fname = cdisp[1]['filename']
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
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue(
            'filename' in cdisp[1],
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))

        fname = cdisp[1]['filename']
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
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue(
            'filename' in cdisp[1],
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        fname = cdisp[1]['filename']
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
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue(
            'filename' in cdisp[1],
            ('Parsed Content-Disposition header doesn\'t contain '
             'filename parameter'))
        fname = cdisp[1]['filename']
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
