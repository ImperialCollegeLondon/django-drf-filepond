# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from io import BytesIO
import logging

import django_drf_filepond.drf_filepond_settings as local_settings
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.core.validators import URLValidator
import requests
from requests.exceptions import ConnectionError
from rest_framework import status
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
import shortuuid

from django_drf_filepond.models import TemporaryUpload, storage, StoredUpload
from django_drf_filepond.parsers import PlainTextParser
from django_drf_filepond.renderers import PlainTextRenderer
import re
import os
import mimetypes
from django.http.response import HttpResponse

LOG = logging.getLogger(__name__)

LOAD_RESTORE_PARAM_NAME = 'id'

def _get_file_id():
    file_id = shortuuid.uuid()
    return file_id

# FIXME: This is a very basic approach to working out the MIME type.
#        It is prone to errors and can be inaccurate since it is 
#        based only on the file extension.
#        A better approach would be to use python-magic but this 
#        introduces another dependency and will likely result in  
#        issues on some platforms.
#        Another option is to store the MIME type in the DB when the 
#        file is uploaded and look this up and return it.
#
# At present this helper function takes only the filename (the data 
# parameter). If this is refactored to use something like python-magic, 
# 'data' will be the header data from the file to enable file type detection. 
def _get_content_type(data, temporary=True):
    return mimetypes.guess_type(data)[0]

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
        if ((not hasattr(local_settings, 'UPLOAD_TMP')) or 
            (not (storage.location).startswith(settings.BASE_DIR))):
            return Response('The file upload path settings are not '
                            'configured correctly.', 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check that we've received a file and then generate a unique ID
        # for it. Also generate a unique UD for the temp upload dir
        file_id = _get_file_id()
        upload_id = _get_file_id()
        
        # By default the upload element name is expected to be "filepond"
        # As raised in issue #4, there are cases where there may be more 
        # than one filepond instance on a page, or the developer has opted 
        # not to use the name "filepond" for the filepond instance.
        # Using the example from #4, this provides support these cases.
        upload_field_name = 'filepond'
        if 'fp_upload_field' in request.data:
            upload_field_name = request.data['fp_upload_field']    
        
        if upload_field_name not in request.data:
            raise ParseError("Invalid request data has been provided.")
            
        file_obj = request.data[upload_field_name]
        
        # Save original file name and set name of saved file to the unique ID
        upload_filename = file_obj.name
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
                             file=file_obj, upload_name=upload_filename, 
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
    
    # Expect the upload ID to be provided with the 'id' parameter
    # This may be either an upload_id that is stored in the StoredUpload
    # table or it may be the path to a file (relative to the fixed upload
    # directory specified by the DJANGO_DRF_FILEPOND_FILE_STORE_PATH 
    # setting parameter). 
    def get(self, request):
        LOG.debug('Filepond API: Load view GET called...')
        
        if ((not hasattr(local_settings, 'FILE_STORE_PATH')) 
            or 
            (not os.path.exists(local_settings.FILE_STORE_PATH))
            or
            (not os.path.isdir(local_settings.FILE_STORE_PATH))
        ):
            return Response('The file upload settings are not configured '
                            'correctly.', 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        file_path_base = local_settings.FILE_STORE_PATH
        
        if LOAD_RESTORE_PARAM_NAME not in request.GET:
            return Response('A required parameter is missing.', 
                            status=status.HTTP_400_BAD_REQUEST)
        
        param_filename = False
        upload_id = request.GET[LOAD_RESTORE_PARAM_NAME]
        
        if (not upload_id) or (upload_id == ''):
            return Response('An invalid ID has been provided.',
                            status=status.HTTP_400_BAD_REQUEST)
        
        upload_id_fmt = re.compile('^([%s]){22}$' 
                                   % (shortuuid.get_alphabet()))
        
        su = None
        if not upload_id_fmt.match(upload_id):
            param_filename = True
            LOG.debug('The provided string doesn\'t seem to be an '
                      'upload ID. Assuming it is a filename/path.')
        else:
            # The provided id could be an upload_id so we can check here.
            try:
                su = StoredUpload.objects.get(upload_id=upload_id)
            except StoredUpload.DoesNotExist:
                LOG.debug('A StoredUpload with the provided ID doesn\'t '
                          'exist. Assuming this could be a filename.')
                param_filename = True
        
        if param_filename:
            # Try and lookup a StoredUpload record with the specified id
            # as the file path
            try:
                su = StoredUpload.objects.get(file_path=upload_id)
            except StoredUpload.DoesNotExist:
                LOG.debug('A StoredUpload with the provided file path '
                          'doesn\'t exist.')
                return Response('Not found', 
                                status=status.HTTP_404_NOT_FOUND)
        
        # su is now the StoredUpload record for the requested file
        
        # See if the stored file with the path specified in su exists 
        # in the file store location
        file_path = os.path.join(file_path_base, su.file_path)
        if ((not os.path.exists(file_path)) or 
            (not os.path.isfile(file_path))):
            return Response('Error reading file...',
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # We now know that the file exists and is a file not a directory
        try:
            with open(file_path, 'rb') as f:
                data = f.read() 
        except IOError as e:
            LOG.error('Error reading requested file: %s' % str(e))
            return Response('Error reading file...',
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        filename = os.path.basename(su.file_path)
        ct = _get_content_type(filename)
        
        response = HttpResponse(data, content_type=ct)
        response['Content-Disposition'] = ('inline; filename=%s' % 
                                           filename)
        
        return response

class RestoreView(APIView):
    
    # Expect the upload ID to be provided with the 'name' parameter
    def get(self, request):
        LOG.debug('Filepond API: Restore view GET called...')
        if LOAD_RESTORE_PARAM_NAME not in request.GET:
            return Response('A required parameter is missing.', 
                            status=status.HTTP_400_BAD_REQUEST)
        
        upload_id = request.GET[LOAD_RESTORE_PARAM_NAME]
        
        upload_id_fmt = re.compile('^([%s]){22}$' % 
                                   (shortuuid.get_alphabet()))
        
        if not upload_id_fmt.match(upload_id):
            return Response('An invalid ID has been provided.',
                            status=status.HTTP_400_BAD_REQUEST)
        
        LOG.debug('Carrying out restore for file ID <%s>' % upload_id)
        
        try:
            tu = TemporaryUpload.objects.get(upload_id=upload_id)
        except TemporaryUpload.DoesNotExist:
            return Response('Not found', status=status.HTTP_404_NOT_FOUND)
        
        upload_file_name = tu.upload_name
        try:
            with open(tu.file.path, 'rb') as f:
                data = f.read() 
        except IOError as e:
            LOG.error('Error reading requested file: %s' % str(e))
            return Response('Error reading file data...',
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        ct = _get_content_type(upload_file_name)
        
        response = HttpResponse(data, content_type=ct)
        response['Content-Disposition'] = ('inline; filename=%s' % 
                                           upload_file_name)
        
        return response

class FetchView(APIView):
        
    def _process_request(self, request):
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
        upload_file_name = None
        try:
            with requests.get(target_url, allow_redirects=True, stream=True) as r:
                if 'Content-Disposition' in r.headers:
                    cd = r.headers['Content-Disposition']
                    matches = re.findall('filename=(.+)', cd)
                    if len(matches):
                        upload_file_name = matches[0]
                for chunk in r.iter_content(chunk_size=1048576):
                    buf.write(chunk)
        except ConnectionError as e:
            raise NotFound('Unable to access the requested remote file: %s'
                           % str(e))
        
        file_id = _get_file_id()
        # If filename wasn't extracted from Content-Disposition header, get
        # from the URL or otherwise set it to the auto-generated file_id
        if not upload_file_name:
            if not target_url.endswith('/'):
                split = target_url.rsplit('/',1)
                upload_file_name = split[1] if len(split) > 1 else split[0]
            else:
                upload_file_name = file_id 
 
        return (buf, file_id, upload_file_name, content_type)    
        
    def head(self, request):
        LOG.debug('Filepond API: Fetch view HEAD called...')
        result = self._process_request(request)
        if isinstance(result, tuple):
            buf, file_id, upload_file_name, content_type = result
        elif isinstance(result, Response):
            return result
        else:
            raise ValueError('process_request result is of an unexpected type')
        
        file_size = buf.seek(0, os.SEEK_END)
        buf.seek(0) 
        
        # The addressing of filepond issue #154 
        # (https://github.com/pqina/filepond/issues/154) means that fetch 
        # can now store a file downloaded from a remote URL and return file 
        # metadata in the header if a HEAD request is received. If we get a  
        # GET request then the standard approach of proxying the file back 
        # to the client is used.
        upload_id = _get_file_id()
        memfile = InMemoryUploadedFile(buf, None, file_id, content_type, 
                                       file_size, None)
        tu = TemporaryUpload(upload_id=upload_id, file_id=file_id,  
                     file=memfile, upload_name=upload_file_name, 
                     upload_type=TemporaryUpload.URL)
        tu.save()
        
        response = Response(status=status.HTTP_200_OK)
        response['Content-Type'] = content_type
        response['Content-Length'] = file_size
        response['X-Content-Transfer-Id'] = upload_id
        response['Content-Disposition'] = ('inline; filename=%s' % 
                                           upload_file_name)
        return response
    
        
    def get(self, request):
        result = self._process_request(request)
        if isinstance(result, tuple):
            buf, _, upload_file_name, content_type = result
        elif isinstance(result, Response):
            return result
        else:
            raise ValueError('process_request result is of an unexpected type')
        response = Response(buf.getvalue(), status=status.HTTP_200_OK, 
                            content_type=content_type)
        response['Content-Disposition'] = ('inline; filename=%s' % 
                                           upload_file_name)
        return response
