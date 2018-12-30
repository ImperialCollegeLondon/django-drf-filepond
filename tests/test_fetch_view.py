import logging

from django.test.testcases import TestCase
from django.urls import reverse
from httpretty import register_uri
import httpretty
import requests
import cgi


LOG = logging.getLogger(__name__)

class FetchTestCase(TestCase):      

    def test_fetch_incorrect_param(self):
        response = self.client.get((reverse('fetch') +
                                     '?somekey=http://localhost/test'))
        self.assertContains(response,'Required query parameter(s) missing.',
                            status_code=400)
    
    def test_fetch_invalid_url(self):
        test_url = 'htt://localhost23/test'
        response = self.client.get((reverse('fetch') + 
                                    ('?target=%s' % test_url)))
        self.assertContains(response,('An invalid URL <%s> has been '
                                      'provided' % test_url),
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
        self.assertContains(response,('Unable to access the requested '
                                      'remote file headers:'),
                                      status_code=500)
    
    @httpretty.activate    
    def test_fetch_file_notfound_error(self):
        test_url = 'http://localhost/test.txt'
        
        register_uri(method=httpretty.HEAD, 
                     uri=test_url,
                     status=404)
        
        response = self.client.get((reverse('fetch') + 
                                    ('?target=%s' % test_url)))
        self.assertContains(response,('The remote file was not found.'),
                                      status_code=404)
        
    @httpretty.activate    
    def test_fetch_http_response_not_allowed(self):
        test_url = 'http://localhost/test.txt'
        def response_callback(request, uri, response_headers):
            response_headers.update({'Content-Type':'text/html'})
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
            response_headers.update({'Content-Type':'text/plain'})
            return [200, response_headers, '']
        
        def response_callback_get(request, uri, response_headers):
            response_headers.update({'Content-Type':'text/plain'})
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
    def test_fetch_with_filename(self):
        filename = 'test.txt'
        test_url = 'http://localhost/%s' % filename
        test_content = '*This is the file content!*'
        
        response = self._filename_fetch_test(test_url, test_content)
        
        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue('filename' in cdisp[1],('Parsed Content-Disposition'
                         ' header doesn\'t contain filename parameter'))
        fname = cdisp[1]['filename']
        self.assertContains(response, '*This is the file content!*',
                            status_code=200)
        self.assertEqual(filename, fname, ('Returned filename is not equal'
                                        ' to the provided filename value.'))
    
    @httpretty.activate  
    def test_fetch_without_filename(self):
        test_url = 'http://localhost/getfile/'
        test_content = '*This is the file content!*'
        
        response = self._filename_fetch_test(test_url, test_content)
        
        self.assertTrue('Content-Disposition' in response,
                        ('Response does not contain a required '
                         'Content-Disposition header.'))
        cdisp = cgi.parse_header(response['Content-Disposition'])
        self.assertTrue('filename' in cdisp[1],('Parsed Content-Disposition'
                         ' header doesn\'t contain filename parameter'))
        fname = cdisp[1]['filename']
        self.assertContains(response, '*This is the file content!*',
                            status_code=200)
        LOG.debug('Returned filename is <%s>' % fname)
        self.assertEqual(len(fname), 22, ('Returned filename is not a 22 '
                                        'character auto-generated name.'))
        #httpretty.register_uri