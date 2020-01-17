'''
Tests for the get_stored_upload-related functions provided by
django-drf-filepond in api.py

Testing of:
    get_stored_upload
    get_stored_upload_file_data
'''
from io import BytesIO
import logging
import os

from django.test import TestCase
from django.utils import timezone

from django_drf_filepond.api import get_stored_upload_file_data
import django_drf_filepond.api
import django_drf_filepond.drf_filepond_settings as local_settings
from django_drf_filepond.exceptions import ConfigurationError
from django_drf_filepond.models import StoredUpload
from django_drf_filepond.views import _get_file_id

# Python 2/3 support
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

# There's no built in FileNotFoundError in Python 2
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

LOG = logging.getLogger(__name__)


#########################################################################
# Tests for get_stored_upload, get_stored_upload_file_data:
#
# test_get_local_stored_upload_data: Check that data is correctly
#    returned for a locally stored upload.
#
# test_get_local_stored_upload_no_filestore: Check that an error is
#    raised if trying to get file data with an unset filestore path
#
# test_get_remote_stored_upload_data: Check that data is correctly
#    returned for a remote upload - test with a mocked SFTP backend.
#
# test_storage_backend_initialised_when_required: Check that when the
#    storage backend is uninitialised, it is set up correctly.
#
# test_get_remote_upload_not_on_remote_store: Check that when requesting
#    a file from a remote store that doesn't exist, we get a suitable error
#
class ApiGetUploadTestCase(TestCase):

    def setUp(self):
        # Set up an initial file upload
        self.upload_id = _get_file_id()
        self.file_id = _get_file_id()
        self.file_content = ('This is some test file data for an '
                             'uploaded file.')
        self.fn = 'my_test_file.txt'
        self.test_target_filename = '/test_storage/testfile.txt'
        self.su = StoredUpload(upload_id=self.upload_id,
                               file=self.test_target_filename[1:],
                               uploaded=timezone.now())
        self.su.save()
        # Create file
        self.file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        file_full_path = os.path.join(self.file_store_path,
                                      self.test_target_filename[1:])
        if not os.path.exists(os.path.dirname(file_full_path)):
            os.mkdir(os.path.dirname(file_full_path))
        with open(file_full_path, 'w') as f:
            f.write(self.file_content)

    def test_store_upload_unset_file_store_path(self):
        (filename, bytes_io) = get_stored_upload_file_data(self.su)
        file_data = bytes_io.read().decode()
        self.assertEqual(file_data, self.file_content,
                         'Returned file content not correct.')
        self.assertEqual(filename, os.path.basename(self.test_target_filename),
                         'Returned file name is not correct.')

    def test_get_local_stored_upload_no_filestore(self):
        fsp = local_settings.FILE_STORE_PATH
        local_settings.FILE_STORE_PATH = None
        with self.assertRaisesMessage(
                ConfigurationError,
                'The file upload settings are not configured correctly.'):
            get_stored_upload_file_data(self.su)
        local_settings.FILE_STORE_PATH = fsp

    def test_get_remote_stored_upload_data(self):
        # Set up the mock_storage_backend.open to return the file content
        mock_storage_backend = self._setup_mock_storage_backend()
        mock_storage_backend.open.return_value = BytesIO(
            self.file_content.encode())
        mock_storage_backend.exists.return_value = True
        (filename, bytes_io) = get_stored_upload_file_data(self.su)
        file_data = bytes_io.read().decode()
        local_settings.STORAGES_BACKEND = None
        django_drf_filepond.api.storage_backend = None
        self.assertEqual(file_data, self.file_content,
                         'Returned file content not correct.')
        self.assertEqual(filename, os.path.basename(self.test_target_filename),
                         'Returned file name is not correct.')

    def test_storage_backend_initialised_when_required(self):
        mock_storage_backend = self._setup_mock_storage_backend()
        mock_storage_backend.open.return_value = BytesIO(
            self.file_content.encode())
        mock_storage_backend.exists.return_value = True
        with patch('django_drf_filepond.api._init_storage_backend') as m:
            django_drf_filepond.api.storage_backend_initialised = False
            get_stored_upload_file_data(self.su)
            local_settings.STORAGES_BACKEND = None
            django_drf_filepond.api.storage_backend = None
            try:
                m.assert_called_once()
            # No assert_called_once on Python 3.5
            except AttributeError:
                self.assertEqual(
                    m.call_count, 1,
                    ('Expected _init_storage_backend to be called once but '
                     'it has been called %s times.' % m.call_count))

    def test_get_remote_upload_not_on_remote_store(self):
        # File store path for remote testing should be ''
        file_store_path = ''
        mock_storage_backend = self._setup_mock_storage_backend()
        mock_storage_backend.exists.return_value = False
        file_path = os.path.join(file_store_path, self.su.file.name)
        with self.assertRaisesMessage(
                FileNotFoundError,
                ('File [%s] for upload_id [%s] not found on remote '
                 'file store.' % (file_path, self.su.upload_id))):
            get_stored_upload_file_data(self.su)
            local_settings.STORAGES_BACKEND = None
            django_drf_filepond.api.storage_backend = None

    def _setup_mock_storage_backend(self):
        # Set storage backend to sftp storage
        local_settings.STORAGES_BACKEND = \
            'storages.backends.sftpstorage.SFTPStorage'

        # Set up mocked objects for storage backend testing
        # Setting up a mock for the storage backend based on examples at
        # https://docs.python.org/3.7/library/unittest.mock-examples.html# \
        # applying-the-same-patch-to-every-test-method
        patcher = patch('storages.backends.sftpstorage.SFTPStorage')
        patcher.start()
        self.addCleanup(patcher.stop)

        # Mock the temporary storage object so that we're not unnecessarily
        # saving files to the local file system.
        patcher2 = patch('django.core.files.storage.FileSystemStorage')
        patcher2.start()
        self.addCleanup(patcher2.stop)
        # Set the backend initialisation flag to false to force re-init
        django_drf_filepond.api.storage_backend_initialised = False
        django_drf_filepond.api._init_storage_backend()
        mock_storage_backend = django_drf_filepond.api.storage_backend
        return mock_storage_backend

    def tearDown(self):
        # Delete stored upload
        self.su.delete()

        # Delete files
        filestore_base = getattr(local_settings, 'FILE_STORE_PATH', None)
        test_stored_file = os.path.join(filestore_base,
                                        self.test_target_filename[1:])
        test_target_dir = os.path.dirname(test_stored_file)

        # Remove test_stored_file
        if (os.path.exists(test_stored_file) and
                os.path.isfile(test_stored_file)):
            LOG.debug('Removing test stored file: <%s>' % test_stored_file)
            os.remove(test_stored_file)
        # Remove directory
        if (os.path.exists(test_target_dir) and
                os.path.isdir(test_target_dir)):
            LOG.debug('Removing test target dir: <%s>' % test_target_dir)
            os.rmdir(test_target_dir)
