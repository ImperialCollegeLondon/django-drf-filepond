'''
Created on 24 Oct 2018

@author: jcohen02

A renderers module to host a PlainTextRenderer that will render
plain text responses sending back the raw text to the client.
'''
from rest_framework.renderers import BaseRenderer
import json
from collections import OrderedDict

# This plaintext renderer is taken from the example in the 
# django rest framework docs since this provides exactly what we 
# require but doesn't seem to be included in the core DRF API.
# See: https://www.django-rest-framework.org/api-guide/renderers/#custom-renderers
# This renderer avoids the issue with the standard JSONRenderer that 
# results in raw text responses being wrapped in quotes.
class PlainTextRenderer(BaseRenderer):
    '''
    Plain text renderer.
    '''
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        '''
        Encode the raw data - default charset is UTF-8.
        '''
        print('Data is <%s>' % data)
        
        if data:
            if type(data) in [dict, OrderedDict]:
                return json.dumps(data)
            else:
                return data.encode(self.charset)
        return data