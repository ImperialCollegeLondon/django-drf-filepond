'''
Created on 24 Oct 2018

@author: jcohen02

A parsers module to host a PlainTextParser that will parse
incoming plain/text requests from filepond
'''
from rest_framework.parsers import BaseParser


# This plaintext parser is taken from the example in the
# django rest framework docs since this provides exactly what we
# require but doesn't seem to be included in the core DRF API.
# See: https://www.django-rest-framework.org/api-guide/parsers/#example
# This will make the data from the body of the request available
# in request.data
class PlainTextParser(BaseParser):
    """
    Plain text parser.
    """
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Simply return a string representing the body of the request.
        """
        return stream.read()


# The chunk parser is used to parse uploaded file chunks for the chunked
# upload support. A chunk upload request has a content type of
# application/offset+octet-stream. For now we simply get the raw request data
# and return it.
# TODO: This could alse extract metadata from the request, such as chunk
#       length, name and offset and return an object containing the data and
#       the metadata. For now the metadata is extracted and checked prior to
#       accessing the uploaded data.
class UploadChunkParser(BaseParser):
    """
    Upload chunk parser for handling uploaded partial file chunks
    """
    media_type = 'application/offset+octet-stream'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        For now just return the body which contains the uploaded file data
        """
        return stream.read()
