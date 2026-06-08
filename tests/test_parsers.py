import os
from io import BytesIO

from rest_framework.exceptions import ParseError
from django_drf_filepond.parsers import PlainTextParser, UploadChunkParser
from django.test import RequestFactory
from django.test.testcases import TestCase


#########################################################################
# Test any custom parsers within parsers.py
#
# test_upload_chunk_parser: The upload chunk parser is used for DRF
#    to handle incoming uploaded file chunks. For now this is just a
#    placeholder that returns the input data unchanged. This test simply
#    checks that the UploadChunkParser returns the input data unchanged.
#
# test_upload_chunk_parser_media_type: Check the UploadChunkParser is
#    setup with the correct media type: 'application/offset+octet-stream'
#
# test_upload_chunk_parser_oversize_content_length: Check that a chunk
#    upload request with a content length larger than the permitted
#    size results in an exception.
#
# test_upload_chunk_parser_oversize_data: Check that a chunk upload
#    request with a valid content length but data that is larger than
#    the permitted size results in an exception.
#
# test_upload_chunk_parser_missing_headers: Check that a chunk upload
#    request with missing Upload-Length or Upload-Offset headers results
#    in an exception.
#
# test_upload_chunk_parser_offset_gt_length: Check that a chunk upload
#    request results in an exception where the chunk offset bytes header
#    value is larger than Upload-Length value.
#
# test_plain_text_parser: Test the plain text parser used by the revert
#    view. The revert view receives DELETE requests that contain the ID
#    of the upload to revert. This shouldn't be more than a small number
#    of characters but we enforce a maximum content length of 512 bytes.
#
# test_plain_text_parser_media_type: Check the PlainTextParser is
#    setup with the correct media type: 'text/plain'
#
# test_plain_text_parser_oversize_content_length: Test the plain text
#    parser raises an exception when the content length of the request
#    exceeds the maximum allowed content length.
#
# test_plain_text_parser_oversize_content: Test the plain text parser
#    raises an exception when the content length of the request is OK
#    but this is incorrect and data exceeds the maximum allowed size.
#
class ParsersTestCase(TestCase):

    def setUp(self):
        # Create a requestfactory that we can use for testing.
        self.rf = RequestFactory()

    def test_upload_chunk_parser(self):
        '''The upload chunk parser is used for DRF to handle incoming
           uploaded file chunks. For now this is just a placeholder that
           returns the input data unchanged. This test simply checks that
           the UploadChunkParser returns the input data unchanged.'''

        # Create a request that we need for testing when the parser checks
        # request content.
        req = self.rf.patch(
            '/patch/ababab',
            headers={'Upload-Length': '1048576', 'Upload-Offset': '0'})
        rq = {'request': req}

        parser = UploadChunkParser()
        randbytes = os.urandom(256)
        stream = BytesIO(randbytes)
        stream.seek(0)
        randbytes2 = parser.parse(stream, parser_context=rq)
        self.assertEqual(randbytes, randbytes2)

    def test_upload_chunk_parser_media_type(self):
        '''Check the UploadChunkParser is setup with the correct media
           type: 'application/offset+octet-stream' '''
        parser = UploadChunkParser()
        self.assertEqual(parser.media_type, 'application/offset+octet-stream')

    def test_upload_chunk_parser_oversize_content_length(self):
        '''
        Check that a chunk upload request with a content length larger
        than the permitted size results in an exception.
        '''
        req = self.rf.patch(
            '/patch/ababab',
            headers={'Upload-Length': '1000000', 'Upload-Offset': '0',
                     'Content-Length': '5000001'})
        rq = {'request': req}

        parser = UploadChunkParser()
        randbytes = os.urandom(256)
        stream = BytesIO(randbytes)
        stream.seek(0)
        with self.assertRaisesMessage(
                ParseError,
                'Chunk larger than maximum allowed chunk data size'):
            parser.parse(stream, parser_context=rq)

    def test_upload_chunk_parser_oversize_data(self):
        '''
        Check that a chunk upload request with a valid content length but
        data that is larger than the permitted size results in an exception.
        '''
        req = self.rf.patch(
            '/patch/ababab',
            headers={'Upload-Length': '1048576', 'Upload-Offset': '0'})
        rq = {'request': req}

        parser = UploadChunkParser()
        randbytes = os.urandom(5000001)
        stream = BytesIO(randbytes)
        stream.seek(0)
        with self.assertRaisesMessage(
                ParseError,
                'Request body larger than chunk data limit.'):
            parser.parse(stream, parser_context=rq)

    def test_upload_chunk_parser_missing_headers(self):
        '''
        Check that a chunk upload request with missing Upload-Length or
        Upload-Offset headers results in an exception.
        '''
        req1 = self.rf.patch(
            '/patch/ababab',
            headers={'Upload-Offset': '0'})
        req2 = self.rf.patch(
            '/patch/ababab',
            headers={'Upload-Length': '1048576'})

        parser = UploadChunkParser()
        randbytes = os.urandom(512)
        stream = BytesIO(randbytes)
        stream.seek(0)

        # Test missing Upload-Length header
        rq = {'request': req1}
        with self.assertRaisesMessage(
                ParseError,
                'Required headers missing in chunk upload request'):
            parser.parse(stream, parser_context=rq)

        # Test missing Upload-Offset header
        rq = {'request': req2}
        stream.seek(0)
        with self.assertRaisesMessage(
                ParseError,
                'Required headers missing in chunk upload request'):
            parser.parse(stream, parser_context=rq)

    def test_upload_chunk_parser_offset_gt_length(self):
        '''
        Check that a chunk upload request results in an exception where the
        chunk offset bytes header value is larger than Upload-Length value.
        '''
        req = self.rf.patch(
            '/patch/ababab',
            headers={'Upload-Length': '1048576', 'Upload-Offset': '1048577'})
        rq = {'request': req}

        parser = UploadChunkParser()
        randbytes = os.urandom(512)
        stream = BytesIO(randbytes)
        stream.seek(0)
        with self.assertRaisesMessage(
                ParseError,
                'Current chunk offset greater than total file size'):
            parser.parse(stream, parser_context=rq)

    def test_plain_text_parser(self):
        # Create a request that we need for testing when the parser checks
        # request content.
        req = self.rf.delete(
            '/patch/ababab',
            headers={'Content-Length': '256'})
        rq = {'request': req}

        parser = PlainTextParser()
        randbytes = os.urandom(256)
        stream = BytesIO(randbytes)
        stream.seek(0)
        randbytes2 = parser.parse(stream, parser_context=rq)
        self.assertEqual(randbytes, randbytes2)

    def test_plain_text_parser_media_type(self):
        '''Check the PlainTextParser is setup with the correct media
           type: 'text/plain' '''
        parser = PlainTextParser()
        self.assertEqual(parser.media_type, 'text/plain')

    def test_plain_text_parser_oversize_content_length(self):
        '''
        Test the plain text parser raises an exception when the content
        length of the request exceeds the maximum allowed content length.
        '''
        req = self.rf.delete(
            '/patch/ababab',
            headers={'Content-Length': '1024'})
        rq = {'request': req}

        parser = PlainTextParser()
        randbytes = os.urandom(5)
        stream = BytesIO(randbytes)
        stream.seek(0)
        with self.assertRaisesMessage(
                ParseError,
                'Request content is greater than allowed size.'):
            parser.parse(stream, parser_context=rq)

    def test_plain_text_parser_oversize_content(self):
        '''
        Test the plain text parser raises an exception when the content
        length of the request is OK but this is incorrect and data exceeds
        the maximum allowed size.
        '''
        req = self.rf.delete(
            '/patch/ababab',
            headers={'Content-Length': '5'})
        rq = {'request': req}

        parser = PlainTextParser()
        randbytes = os.urandom(1024)
        stream = BytesIO(randbytes)
        stream.seek(0)
        with self.assertRaisesMessage(
                ParseError,
                'Request body larger than data limit.'):
            parser.parse(stream, parser_context=rq)
