# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from io import BytesIO
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import URLValidator
import requests
from requests.exceptions import ConnectionError
from rest_framework import status
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
import shortuuid

from django_drf_filepond.models import TemporaryUpload, storage
from django_drf_filepond.parsers import PlainTextParser
from django_drf_filepond.renderers import PlainTextRenderer
import os


LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger(__name__).setLevel(logging.DEBUG)

def _get_file_id():
    file_id = shortuuid.uuid()
    return file_id

class ProcessView(APIView):
    '''
    This view receives an uploaded file from the filepond client. It
    stores the file in a temporary location and generates a unique ID which 
    it associates with the temporary upload. The unique ID is returned to 
    the client. If and when the parent form is finally submitted, the unique 
    ID is provided and the file is then moved from the temporary store into 
    permanent storage in line with the requirements of the parent application.  
    '''
    # This view uses the MultiPartParser to parse the uploaded file data
    # from FilePond.
    parser_classes = (MultiPartParser,)
    renderer_classes = (PlainTextRenderer,)
    
    def post(self, request):
        LOG.debug('Filepond API: Process view POST called...')
        
        # Enforce that the upload location must be a sub-directory of 
        # the project base directory
        # TODO: Check whether this is necessary - maybe add a security 
        # parameter that can be disabled to turn off this check if the 
        # developer wishes?
        if ((not hasattr(settings, 'DJANGO_DRF_FILEPOND_UPLOAD_TMP')) and 
            (not (storage.location).startswith(settings.BASE_DIR))):
            return Response('The file upload path settings are not '
                            'configured correctly.', 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check that we've received a file and then generate a unique ID
        # for it. Also generate a unique UD for the temp upload dir
        file_id = _get_file_id()
        upload_id = _get_file_id()
        
        if 'filepond' not in request.data:
            raise ParseError("Invalid request data has been provided.")
            
        file_obj = request.data['filepond']
        
        # Save original file name and set name of saved file to the unique ID
        upload_name = file_obj.name
        file_obj.name = file_id
        
        # The type of parsed data should be a descendant of an UploadedFile
        # type.
        if not isinstance(file_obj, UploadedFile):
            raise ParseError('Invalid data type has been parsed.')
        
        # Before we attempt to save the file, make sure that the upload  
        # directory we're going to save to exists.
        # *** It's not necessary to explicitly create the directory since
        # *** the FileSystemStorage object creates the directory on save
        #if not os.path.exists(storage.location):
        #    LOG.debug('Filepond app: Creating file upload directory '
        #             '<%s>...' % storage.location)
        #    os.makedirs(storage.location, mode=0o700)
        
        # We now need to create the temporary upload object and store the 
        # file and metadata.
        tu = TemporaryUpload(upload_id=upload_id, file_id=file_id,  
                             file=file_obj, upload_name=upload_name, 
                             upload_type=TemporaryUpload.FILE_DATA)
        tu.save()
        
        response = Response(upload_id, status=status.HTTP_200_OK, 
                            content_type='text/plain')
        return response

class RevertView(APIView):
    
    parser_classes = (PlainTextParser,)
    renderer_classes = (PlainTextRenderer,)
    '''
    This is called when we need to revert the uploaded file - i.e. undo is
    pressed and we remove the previously uploaded temporary file.
    '''
    def delete(self, request):
        # If we've received the incoming data as bytes, we need to decode 
        # it to a string
        if type(request.data) == type(b''):
            request_data = request.data.decode('utf-8')
        else:
            request_data = request.data
        
        # Expecting a 22-character unique ID telling us which temporary 
        # upload to remove.
        LOG.debug('Filepond API: Revert view DELETE called...')
        upload_id = request_data.strip()
        
        if len(upload_id) != 22:
            raise ParseError('The provided data is invalid.')
        
        # Lookup the temporary file record
        try:
            tu = TemporaryUpload.objects.get(upload_id=upload_id)
            LOG.debug('About to delete temporary upload <%s> with original '
                      'filename <%s>' % (tu.upload_id, tu.upload_name))
            tu.delete()
        except TemporaryUpload.DoesNotExist:
            raise NotFound('The specified file does not exist.')
        
        return Response(status=status.HTTP_204_NO_CONTENT)

class LoadView(APIView):
    def get(self, request):
        LOG.debug('Filepond API: Load view GET called...')
        raise NotImplementedError('The load function is not yet implemented')

class RestoreView(APIView):
    def get(self, request):
        LOG.debug('Filepond API: Restore view GET called...')
        raise NotImplementedError('The restore function is not yet implemented')

class FetchView(APIView):
    def get(self, request):
        LOG.debug('Filepond API: Fetch view GET called...')
        '''
        Supports retrieving a file on the server side that the user has 
        specified by calling addFile on the filepond API and passing a 
        URL to a file.
        '''
        # Retrieve the target URL from the request query string target
        # target parameter, pull the file into temp upload storage and 
        # return a file object.
        
        # First check we have a URL and parse to check it's valid
        target_url = request.query_params.get('target', None)
        if not target_url:
            raise ParseError('Required query parameter(s) missing.')
        
        # Use Django's URL validator to see if we've been given a valid URL
        validator = URLValidator(message=('An invalid URL <%s> has been '
                                          'provided' % (target_url)))
        try:
            validator(target_url)
        except ValidationError as e:
            raise ParseError(str(e))
        
        # TODO: SHould we check the headers returned when we request the 
        # download to see that we're getting a file rather than an HTML page? 
        # For now this check is enabled on the basis that we assume target 
        # data file will not be HTML. However, there should be a way to turn
        # this off if the client knows that they want to get an HTML file.
        # TODO: *** Looks like this use of head can be removed since with 
        # the new approach of streaming content to a BytesIO object, when 
        # stream=True, the connection begins by being opened and only 
        # fetching the headers. We could do this check then.
        try:
            header = requests.head(target_url, allow_redirects=True)
        except ConnectionError as e:
            msg = ('Unable to access the requested remote file headers: %s' 
                   % str(e))
            LOG.error(msg)
            return Response(msg, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if header.status_code == 404:
            raise NotFound('The remote file was not found.')

        content_type = header.headers.get('Content-Type','')
        
        # If the URL has returned URL content but an HTML file was not 
        # requested then assume that the URL has linked to a download page or
        # some sort of error page or similar and raise an error.
        if 'html' in content_type.lower() and '.html' not in target_url:
            LOG.error('The requested data seems to be in HTML format. '
                      'Assuming this is not valid data file.')
            raise ParseError('Provided URL links to HTML content.')
        
        buf = BytesIO()
        try:
            with requests.get(target_url, allow_redirects=True, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1048576):
                    buf.write(chunk)
        except ConnectionError as e:
            raise NotFound('Unable to access the requested remote file: %s'
                           % str(e))
        
        #content_length = buf.tell()
        # Generate a default filename and then if we can extract the 
        # filename from the URL, replace the default name with the one from 
        # the URL. 
        file_id = _get_file_id()
        upload_file_name = file_id
        if not target_url.endswith('/'):
            split = target_url.rsplit('/',1)
            upload_file_name = split[1] if len(split) > 1 else split[0] 
            
        # FIXME: After examining the approach used by fetch in the 
        # php-boilerplate, it seems that this part of the API is simply used 
        # to proxy a request to download a file at a specified URL - this 
        # seems inefficient since the file is sent back to the client and 
        # then uploaded again to the server. 
        ## Create the file name for the data to be saved. Also get the 
        ## original name from the request.
        ## There is an issue here in that we need to create a Python file
        ## object to be wrapped as a Django "File". However, in doing this, 
        ## the file is created. When we save the TemporaryUpload object it 
        ## calls save on the FileField which then fails because it finds that
        ## the filename is taken, tries to create an extended alternative 
        ## name and this goes outside the 22 character require length.
        ## As a workaround, creating a Django InMemoryUploadedFile instead 
        ## and using this as the file that will be written to disk.
        #memfile = InMemoryUploadedFile(buf, None, file_id, content_type, 
        #                               content_length, None)
        ##filename = os.path.join(storage.base_location, file_id)
        ##with open(filename, 'w') as f:
        ##    file_obj = File(f)        
        #tu = TemporaryUpload(file_id=file_id, file=memfile, 
        #                     upload_name=upload_file_name, 
        #                     upload_type=TemporaryUpload.URL)
        #tu.save()
    
        response = Response(buf.getvalue(), status=status.HTTP_200_OK, 
                            content_type=content_type)
        response['Content-Disposition'] = ('inline; filename="%s"' % 
                                           upload_file_name)
        return response

