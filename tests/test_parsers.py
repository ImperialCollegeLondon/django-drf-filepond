import os
from io import BytesIO
from django_drf_filepond.parsers import UploadChunkParser
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

class ParsersTestCase(TestCase):

    def test_upload_chunk_parser(self):
        '''The upload chunk parser is used for DRF to handle incoming
           uploaded file chunks. For now this is just a placeholder that
           returns the input data unchanged. This test simply checks that
           the UploadChunkParser returns the input data unchanged.'''
        parser = UploadChunkParser()
        randbytes = os.urandom(256)
        stream = BytesIO(randbytes)
        stream.seek(0)
        randbytes2 = parser.parse(stream)
        self.assertEqual(randbytes, randbytes2)

    def test_upload_chunk_parser_media_type(self):
        '''Check the UploadChunkParser is setup with the correct media
           type: 'application/offset+octet-stream' '''
        parser = UploadChunkParser()
        self.assertEqual(parser.media_type, 'application/offset+octet-stream')
