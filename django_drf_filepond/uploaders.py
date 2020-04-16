import logging

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response

from django_drf_filepond.models import TemporaryUpload
from django.contrib.auth.models import AnonymousUser

LOG = logging.getLogger(__name__)


# Get the user associated with the provided request. If we have an anonymous
# user object then return None
def _get_user(request):
    upload_user = getattr(request, 'user', None)
    if isinstance(upload_user, AnonymousUser):
        upload_user = None
    return upload_user


class FilepondFileUploader(object):

    @classmethod
    def get_uploader(cls, request):
        # Process the request to identify if it's a standard upload request
        # or a request that is related to a chunked upload. Return the right
        # kind of uploader to handle this.

        LOG.debug('Returning STANDARD uploader to handle upload request... ')
        return FilepondStandardFileUploader()

        # LOG.debug('Returning CHUNKED uploader to handle upload request... ')
        # return FilepondChunkedFileUploader()


class FilepondStandardFileUploader(FilepondFileUploader):

    def handle_upload(self, request, file_id, upload_id):
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
        # if not os.path.exists(storage.location):
        #    LOG.debug('Filepond app: Creating file upload directory '
        #             '<%s>...' % storage.location)
        #    os.makedirs(storage.location, mode=0o700)

        LOG.debug('About to store uploaded temp file with filename: %s'
                  % (upload_filename))

        # We now need to create the temporary upload object and store the
        # file and metadata.
        tu = TemporaryUpload(upload_id=upload_id, file_id=file_id,
                             file=file_obj, upload_name=upload_filename,
                             upload_type=TemporaryUpload.FILE_DATA,
                             uploaded_by=_get_user(request))
        tu.save()

        response = Response(upload_id, status=status.HTTP_200_OK,
                            content_type='text/plain')

        return response



class FilepondChunkedFileUploader(FilepondFileUploader):

    def handle_upload(self, request):
        pass