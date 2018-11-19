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