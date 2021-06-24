# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import importlib
import logging
import mimetypes

import django_drf_filepond.drf_filepond_settings as local_settings
import os
import re
import requests
import shortuuid
import django_drf_filepond
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator
from django.http.response import HttpResponse, HttpResponseNotFound, \
    HttpResponseServerError
from django_drf_filepond.api import get_stored_upload, \
    get_stored_upload_file_data
from django_drf_filepond.exceptions import ConfigurationError
from django_drf_filepond.models import TemporaryUpload, storage, StoredUpload
from django_drf_filepond.parsers import PlainTextParser, UploadChunkParser
from django_drf_filepond.renderers import PlainTextRenderer
from io import BytesIO
from requests.exceptions import ConnectionError
from rest_framework import status
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_drf_filepond.uploaders import FilepondFileUploader
from django_drf_filepond.utils import _get_file_id, _get_user,\
    get_local_settings_base_dir

LOG = logging.getLogger(__name__)

LOAD_RESTORE_PARAM_NAME = 'id'


# There's no built in FileNotFoundError in Python 2
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


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


def _import_permission_classes(endpoint):
    """
    Iterates over array of string representations of permission classes from
    settings specified.
    """
    permission_classes = []
    if endpoint in local_settings.PERMISSION_CLASSES.keys():
        for perm_str in local_settings.PERMISSION_CLASSES[endpoint]:
            (modname, clname) = perm_str.rsplit('.', 1)
            mod = importlib.import_module(modname)
            class_ = getattr(mod, clname)
            permission_classes.append(class_)
    return permission_classes


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
    permission_classes = _import_permission_classes('POST_PROCESS')

    def post(self, request):
        LOG.debug('Filepond API: Process view POST called...')

        # Check that the temporary upload directory has been set
        if not hasattr(local_settings, 'UPLOAD_TMP'):
            return Response('The file upload path settings are not '
                            'configured correctly.',
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # By default, enforce that the temporary upload location must be a
        # sub-directory of the project base directory.
        # TODO: Check whether this is necessary - maybe add a security
        # parameter that can be disabled to turn off this check if the
        # developer wishes?
        LOCAL_BASE_DIR = get_local_settings_base_dir()
        if ((not (storage.location).startswith(LOCAL_BASE_DIR)) and
                (LOCAL_BASE_DIR !=
                 os.path.dirname(django_drf_filepond.__file__))):
            if not local_settings.ALLOW_EXTERNAL_UPLOAD_DIR:
                return Response('The file upload path settings are not '
                                'configured correctly.',
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check that a relative path is not being used to store the
        # upload outside the specified UPLOAD_TMP directory.
        if not getattr(local_settings, 'UPLOAD_TMP').startswith(
                os.path.abspath(storage.location)):
            return Response('An invalid storage location has been '
                            'specified.',
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check that we've received a file and then generate a unique ID
        # for it. Also generate a unique UD for the temp upload dir
        file_id = _get_file_id()
        upload_id = _get_file_id()

        try:
            uploader = FilepondFileUploader.get_uploader(request)
            response = uploader.handle_upload(request, file_id, upload_id)
        except ParseError as e:
            # Re-raise the ParseError to trigger a 400 response via DRF.
            raise e

        return response


class PatchView(APIView):
    '''
    This view handles a PATCH request containing a file chunk as part of the
    filepond chunked upload support. The chunk will relate to an existing
    chunked upload configuration created when a new chunked upload request
    was made to the ProcessView.
    See: https://pqina.nl/filepond/docs/patterns/api/server/#process-chunks
    for details of how chunked uploads are handled in filepond.
    Assuming everything in the request is valid, this view will store the
    chunk.
    '''
    # Chunk upload PATCH requests use the application/offset+octet-stream
    # Content-Type. Since this is different to the multipart upload used for
    # process requests, this is being handled in a separate view.
    # from FilePond.
    parser_classes = (UploadChunkParser,)
    renderer_classes = (PlainTextRenderer,)
    permission_classes = _import_permission_classes('PATCH_PATCH')

    def patch(self, request, chunk_id):
        LOG.debug('Filepond API: Patch view PATCH called...')
        uploader = FilepondFileUploader.get_uploader(request)
        return uploader.handle_upload(request, chunk_id)

    # The HEAD method is used to request information about a partially
    # completed chunked upload. Assuming the details are found and returned
    # correctly, the client will use this to restart a failed chunked upload.
    def head(self, request, chunk_id):
        LOG.debug('Filepond API: Patch view HEAD called...')
        uploader = FilepondFileUploader.get_uploader(request)
        return uploader.handle_upload(request, chunk_id)


class RevertView(APIView):

    parser_classes = (PlainTextParser,)
    renderer_classes = (PlainTextRenderer,)
    permission_classes = _import_permission_classes('DELETE_REVERT')
    '''
    This is called when we need to revert the uploaded file - i.e. undo is
    pressed and we remove the previously uploaded temporary file.
    '''
    def delete(self, request):
        # If we've received the incoming data as bytes, we need to decode
        # it to a string
        if isinstance(request.data, bytes):
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
    """
    Expect the upload ID to be provided with the 'id' parameter
    This may be either an upload_id that is stored in the StoredUpload
    table or it may be the path to a file (relative to the fixed upload
    directory specified by the DJANGO_DRF_FILEPOND_FILE_STORE_PATH
    setting parameter).
    """
    permission_classes = _import_permission_classes('GET_LOAD')

    def get(self, request):
        LOG.debug('Filepond API: Load view GET called...')

        if LOAD_RESTORE_PARAM_NAME not in request.GET:
            return Response('A required parameter is missing.',
                            status=status.HTTP_400_BAD_REQUEST)

        upload_id = request.GET[LOAD_RESTORE_PARAM_NAME]

        if (not upload_id) or (upload_id == ''):
            return Response('An invalid ID has been provided.',
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            su = get_stored_upload(upload_id)
        except StoredUpload.DoesNotExist as e:
            LOG.error('StoredUpload with ID [%s] not found: [%s]'
                      % (upload_id, str(e)))
            return Response('Not found', status=status.HTTP_404_NOT_FOUND)

        # su is now the StoredUpload record for the requested file
        try:
            (filename, data_bytes) = get_stored_upload_file_data(su)
        except ConfigurationError as e:
            LOG.error('Error getting file upload: [%s]' % str(e))
            return HttpResponseServerError('The file upload settings are '
                                           'not configured correctly.')
        except FileNotFoundError:
            return HttpResponseNotFound('Error accessing file, not found.')
        except IOError:
            return HttpResponseServerError('Error reading file...')

        ct = _get_content_type(filename)

        response = HttpResponse(data_bytes, content_type=ct)
        response['Content-Disposition'] = ('inline; filename=%s' %
                                           filename)

        return response


class RestoreView(APIView):
    permission_classes = _import_permission_classes('GET_RESTORE')

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
    permission_classes = _import_permission_classes('GET_FETCH')

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

        content_type = header.headers.get('Content-Type', '')

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
            with requests.get(target_url,
                              allow_redirects=True, stream=True) as r:
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
                split = target_url.rsplit('/', 1)
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
                             upload_type=TemporaryUpload.URL,
                             uploaded_by=_get_user(request))
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
        response = HttpResponse(buf.getvalue(), content_type=content_type)
        response['Content-Disposition'] = ('inline; filename=%s' %
                                           upload_file_name)
        return response
