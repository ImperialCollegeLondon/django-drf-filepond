# A module containing some utility functions used by the views and uploaders
from io import UnsupportedOperation
import os

import shortuuid
import six
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import UploadedFile
from django.utils.functional import cached_property

import django_drf_filepond.drf_filepond_settings as local_settings
from django_drf_filepond.models import storage


# Get the user associated with the provided request. If we have an anonymous
# user object then return None
def _get_user(request):
    upload_user = getattr(request, 'user', None)
    if isinstance(upload_user, AnonymousUser):
        upload_user = None
    return upload_user


# Generate a file or upload ID. At present, this is used for generating both
# ID types since they both have the same specification.
def _get_file_id():
    file_id = shortuuid.uuid()
    return six.ensure_text(file_id)


# Get the BASE_DIR variable from local_settings and process it to ensure that
# it can be used in django_drf_filepond across Python 2.7, 3.5 and 3.6+.
# Need to take into account that this may be a regular string or a
# pathlib.Path object. django-drf-filepond expects to work with BASE_DIR as a
# string so return a string regardless of the type of BASE_DIR. To maintain
# suport for Python 2.7, need to handle the case where pathlib.Path doesn't
# exist...
def get_local_settings_base_dir():
    base_dir = local_settings.BASE_DIR
    return _process_base_dir(base_dir)


# Process the provided BASE_DIR variable
def _process_base_dir(base_dir):
    try:
        from pathlib import Path
    except ImportError:
        return base_dir

    if isinstance(base_dir, Path):
        return str(base_dir)
    return base_dir


# A custom "django.core.files.uploadedfile.UploadedFile" object that picks
# up the chunked files stored separately on disk for a chunked upload.
# At present, these are "reconstituted" into a BytesIO object and then
# passed to an InMemoryUploadedFile object, however, this results in using
# double the memory of the size of the stored upload which has been causing
# issues for users handling large uploads (see issue #64 - https://github.com
# /ImperialCollegeLondon/django-drf-filepond/issues/64). This uploadded
# file obejct addresses this issue by loading the required chunk data in
# on demand.
# To be able to process the chunks we need the chunk directory, the file_id
# (the filename prefix used for all chunk files), and the number of chunks.
# All this data is obtained from the instance of the TemporaryUploadChunked
# object provided.
class DrfFilepondChunkedUploadedFile(UploadedFile):
    def __init__(self, temp_chunked_upload_model_obj, content_type=None):
        # From superclass __init__
        # file=None, name=None, content_type=None, size=None, charset=None,
        # content_type_extra=None
        super().__init__(None, temp_chunked_upload_model_obj.upload_name)
        # Remove the size attribute so that it is recalulated by the property
        # function.
        delattr(self, 'size')
        self.content_type = content_type
        self.charset = None
        self.content_type_extra = None
        self.chunk_dir = os.path.join(
            storage.base_location,
            temp_chunked_upload_model_obj.upload_dir)
        self.chunk_base = temp_chunked_upload_model_obj.file_id
        self.num_chunks = temp_chunked_upload_model_obj.last_chunk
        self.total_size = temp_chunked_upload_model_obj.total_size
        self.first_file = os.path.join(
            self.chunk_dir, '%s_1' % (self.chunk_base))
        if not os.path.exists(self.first_file):
            raise FileNotFoundError('Initial chunk for this file not found.')
        self.chunk_size = os.path.getsize(self.first_file)

        self.offset = 0
        # 1-indexed value for current chunk (chunks start at 1)
        self.current_chunk = 1

    # Override the parent File class's size property and calculate
    # this based on the all the chunk files.
    @cached_property
    def size(self):
        if os.path.exists(self.chunk_dir):
            size = 0
            try:
                for i in range(self.num_chunks):
                    size += os.path.getsize(os.path.join(
                        self.chunk_dir, '%s_%s' % (self.chunk_base, (i+1))))
            except OSError as e:
                raise AttributeError(
                    'Unable to get the file\'s size: %s' % str(e))
            return size
        raise AttributeError('Unable to determine the file\'s size.')

    def chunks(self, chunk_size=None):
        """
        The file is being read as a series of ``chunk files``. These may
        differ in size to self.chunk_size.

        Read ``chunk_size`` bytes from the current file and yield. If the read
        goes over the end of the current chunk and into the next one, close
        the current file, open the next and continue reading up to chunk_size.
        """
        if self.closed:
            raise OSError('File must be opened with "open(mode)" before '
                          'attempting to read data')
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE

        # Reset ourselves back to the start of the first chunk.
        if self.current_chunk == 1:
            try:
                self.seek(0)
                self.offset = 0
            except (AttributeError, UnsupportedOperation):
                pass
        else:
            self.current_chunk = 1
            self.offset = 0
            self.file = open(self.first_file, self.mode)

        while self.offset < self.total_size:
            print('Current offset: %s' % self.offset)
            chunk_bytes_read = 0
            data = self.read(chunk_size)
            bytes_read = len(data)
            chunk_bytes_read += bytes_read
            self.offset += bytes_read
            print('Offset after initial chunk read: %s' % self.offset)
            while chunk_bytes_read < chunk_size:
                # Open the next file and continue reading
                self.file.close()
                self.current_chunk += 1
                # If we've passed the end of all chunks, break from loop
                if self.current_chunk > self.num_chunks:
                    break
                # Otherwise open the next file and continue reading
                else:
                    self.file = open(os.path.join(
                        self.chunk_dir,
                        '%s_%s' % ((self.chunk_base, self.current_chunk))
                    ), self.file.mode)
                new_data = self.read(chunk_size - chunk_bytes_read)
                bytes_read = len(new_data)
                chunk_bytes_read += bytes_read
                self.offset += bytes_read
                data += new_data
                print('Offset after subsequent chunk read: %s' % self.offset)

            if (not data):
                print('No more data, leaving loop at offset: %s' % self.offset)
                break

            print('Yielding data...')
            yield data

    def multiple_chunks(self, chunk_size=None):
        return True

    def open(self, mode):
        self.mode = mode

        if self.first_file and os.path.exists(self.first_file):
            if not self.closed:
                self.close()

            self.current_chunk = 1
            self.offset = 0
            self.file = open(self.first_file, self.mode)
        else:
            raise ValueError("The file cannot be reopened.")
        return self
