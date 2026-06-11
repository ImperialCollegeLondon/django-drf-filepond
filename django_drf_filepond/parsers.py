'''
Created on 24 Oct 2018

@author: jcohen02

A parsers module to host a PlainTextParser that will parse
incoming plain/text requests from filepond
'''
import django_drf_filepond.drf_filepond_settings as local_settings

from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError


# This plaintext parser is based on the example in the
# django rest framework docs since this provides almost exactly what we
# require but doesn't seem to be included in the core DRF API.
# See: https://www.django-rest-framework.org/api-guide/parsers/#example
# This will make the data from the body of the request available
# in request.data. This is used by the RevertView which receives DELETE
# requests. The DELETE request contains the ID of the upload to delete in
# the request body (https://pqina.nl/filepond/docs/api/server/#revert).
# IDs should be no more than a few characters but to support the potential
# use of other ID schemes with longer IDs, this parser allows requests
# with a body of up to 512 bytes.
class PlainTextParser(BaseParser):
    """
    Plain text parser.
    """
    media_type = 'text/plain'

    PLAIN_TEXT_REQUEST_BODY_BYTES_CAP = 512

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Validate stream and return string representing the body of the request.
        """
        parser_context = parser_context or {}
        request = parser_context['request']
        # Check that the chunk offset doesn't exceed the complete file size.
        content_length = int(request.META.get('CONTENT_LENGTH', 0))
        if content_length > self.PLAIN_TEXT_REQUEST_BODY_BYTES_CAP:
            raise ParseError('Request content is greater than allowed size.')
        # Read the data from the stream but restrict reading to the maximum
        # request body data size (+1 so we can test if the provided data is
        # larger)
        req_data = stream.read(self.PLAIN_TEXT_REQUEST_BODY_BYTES_CAP + 1)
        if len(req_data) > self.PLAIN_TEXT_REQUEST_BODY_BYTES_CAP:
            raise ParseError('Request body larger than data limit.')
        return req_data


# The chunk parser is used to parse uploaded file chunks for the chunked
# upload support. A chunk upload request has a content type of
# application/offset+octet-stream. For now we simply get the raw request data
# and return it.
# TODO: This could also extract metadata from the request, such as chunk
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
        Validate stream and return the uploaded file data
        """
        MAX_CHUNK_DATA_SIZE = local_settings.MAX_CHUNK_DATA_SIZE

        parser_context = parser_context or {}
        request = parser_context['request']
        # Check that the chunk offset doesn't exceed the complete file size.
        content_length = int(request.META.get('CONTENT_LENGTH', 0))
        upload_length = int(request.META.get('HTTP_UPLOAD_LENGTH', -1))
        upload_offset = int(request.META.get('HTTP_UPLOAD_OFFSET', -1))
        if ((upload_length < 0) or (upload_offset < 0)):
            raise ParseError(
                'Required headers missing in chunk upload request')
        if content_length > MAX_CHUNK_DATA_SIZE:
            raise ParseError(
                'Chunk larger than maximum allowed chunk data size')
        if upload_offset > upload_length:
            raise ParseError(
                'Current chunk offset greater than total file size')

        chunk_data = stream.read(MAX_CHUNK_DATA_SIZE + 1)
        if len(chunk_data) > MAX_CHUNK_DATA_SIZE:
            raise ParseError('Request body larger than chunk data limit.')
        return chunk_data
