'''
Tests for the delete_stored_upload api function provided by django-drf-filepond

THIS SET OF TESTS WILL TEST DELETION OF STORED UPLOADS FOR BOTH LOCAL AND
REMOTE STORAGE. IT TESTS THE FUNCTIONALITY OF THE delete_stored_upload
FUNCTION.

delete_stored_upload:
    Deletes a stored upload from the django-drf-filepond database stored
    upload database table and also deletes the associated file from permanent
    storage if the delete_file parameter is set to True.
    The file may be stored on the local filesystem on the host system or
    have been stored to a remote file store via the django-storages library.
    If using a local file store, the base location where files are stored is
    based on the DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting. If using a
    remote file store, the settings for the storage backend determine the
    base file storage location.
'''
import logging
import os

from django.test import TestCase
from django_drf_filepond.views import _get_file_id
from django_drf_filepond.models import StoredUpload

import django_drf_filepond.drf_filepond_settings as local_settings
from django.utils import timezone
from django_drf_filepond.exceptions import ConfigurationError

# Python 2/3 support
try:
    from unittest.mock import MagicMock
    from unittest.mock import patch
except ImportError:
    from mock import MagicMock
    from mock import patch

# There's no built in FileNotFoundError, FileExistsError in Python 2
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

LOG = logging.getLogger(__name__)


##############################################################################
# Tests for upload removal on local/remote storage using delete_stored_upload:
#
# test_delete_stored_upload_local: Call delete_stored_upload with a valid ID
#    and delete_file=True and check that the file is removed.
#
# test_delete_stored_upload_remote: Call delete_stored_upload with a valid ID
#    and delete_file=True and check that the file is removed via a delete
#    call to the django-storages backend.
#
# test_delete_stored_upload_local_keepfile: Call delete_stored_upload with a
#    valid ID and delete_file=False and check that the file is not removed.
#
# test_delete_stored_upload_remote_keepfile: Call delete_stored_upload with a
#    valid ID and delete_file=False and check that the file is not removed
#    by testing that delete on the django-storages backend is not called.
#
# test_delete_stored_upload_invalid_id: Call delete_stored_upload with an
#    invalid ID. Exception expected.
#
# test_delete_stored_upload_local_no_filestore_path: Call delete_stored_upload
#    with local storage and no FILE_STORE_PATH set. Check that we get a
#    ConfigurationError.
#
# test_delete_stored_upload_local_not_exists: Call delete_stored_upload with
#    local storage where FILE_STORE_PATH doesn't exist. Check for a
#    ConfigurationError.
#
# test_delete_stored_upload_local_not_isdir:  Call delete_stored_upload with
#    local storage where FILE_STORE_PATH exists but is not a directory. Check
#    for a ConfigurationError.
#
# test_delete_stored_upload_remote_file_missing: Call delete_stored_upload
#    with a valid upload_id but where the file is missing on the remote
#    storage backend.
#
# test_delete_stored_upload_local_file_missing: Call delete_stored_upload
#    with a valid upload_id but where the file is missing on the local file
#    store.
#
# test_delete_stored_upload_local_remove_fails: Call delete_stored_upload
#    with a valid upload_id but where the file is missing on the local file
#
class ApiDeleteTestCase(TestCase):

    def setUp(self):
        self.storage_backend = local_settings.STORAGES_BACKEND
        # Set storage backend to sftp storage
        local_settings.STORAGES_BACKEND = \
            'storages.backends.sftpstorage.SFTPStorage'

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
        # Reinitialse stored upload after we changed the STORAGES_BACKEND
        # class name above. This ensures that we're looking at the mocked
        # backend class.
        import django_drf_filepond.api
        self.api = django_drf_filepond.api
        django_drf_filepond.api.storage_backend_initialised = False
        django_drf_filepond.api._init_storage_backend()
        self.mock_storage_backend = django_drf_filepond.api.storage_backend
        self.delete_upload = django_drf_filepond.api.delete_stored_upload

        # Check that we're using a mocked storage backend
        self.assertTrue(
            isinstance(django_drf_filepond.api.storage_backend, MagicMock),
            ('The created storage backend should be mocked but it is not of '
             'type unittest.mock.MagicMock...'))

        # Set up a "StoredUpload"
        self.upload_id = _get_file_id()
        self.file_id = _get_file_id()
        # self.file_content = ('This is some test file data for an '
        #                      'uploaded file.')
        self.fn = 'my_test_file.txt'
        self.test_target_filepath = os.path.join('test_storage', self.fn)
        self.su = StoredUpload(upload_id=self.upload_id,
                               file=self.test_target_filepath,
                               uploaded=timezone.now(),
                               stored=timezone.now())
        self.su.save()

    def test_delete_stored_upload_local(self):
        # Make an API call to delete the stored upload and check that delete
        # is called on the FileSystemStorage backend.
        # Set the storage backend to None to force use of local storage.
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False

        # Get the target file path that we want to check that delete has been
        # called with. This is the file path from the DB plus the base file
        # system storage location.
        base_store_location = local_settings.FILE_STORE_PATH
        file_location = os.path.join(base_store_location,
                                     self.test_target_filepath)

        with patch('os.remove') as os_patcher:
            with patch('os.path.exists') as exists:
                with patch('os.path.isfile') as isfile:
                    exists.return_value = True
                    isfile.return_value = True
                    self.delete_upload(self.upload_id, delete_file=True)
                    with self.assertRaises(StoredUpload.DoesNotExist):
                        StoredUpload.objects.get(upload_id=self.upload_id)
                    os_patcher.assert_called_once_with(file_location)

    def test_delete_stored_upload_remote(self):
        self.mock_storage_backend.exists.return_value = True
        self.delete_upload(self.upload_id, delete_file=True)
        self.mock_storage_backend.delete.assert_called_once_with(
            self.test_target_filepath)

    def test_delete_stored_upload_local_keepfile(self):
        # Make an API call to delete the stored upload and check that delete
        # is called on the FileSystemStorage backend.
        # Set the storage backend to None to force use of local storage.
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False

        with patch('os.remove') as os_patcher:
            with patch('os.path.exists') as exists:
                with patch('os.path.isdir') as isdir:
                    exists.return_value = True
                    isdir.return_value = True
                    self.delete_upload(self.upload_id, delete_file=False)
                    with self.assertRaises(StoredUpload.DoesNotExist):
                        StoredUpload.objects.get(upload_id=self.upload_id)
                    os_patcher.assert_not_called()
                    exists.assert_not_called()
                    isdir.assert_not_called()

    def test_delete_stored_upload_remote_keepfile(self):
        self.delete_upload(self.upload_id, delete_file=False)
        self.mock_storage_backend.exists.assert_not_called()
        self.mock_storage_backend.delete.assert_not_called()

    def test_delete_stored_upload_invalid_id(self):
        test_id = 'abcdefghijklmnopqrstuv'
        ('No stored upload found with the specified ID [%s].' % (test_id))
        with self.assertRaisesMessage(
                StoredUpload.DoesNotExist,
                'StoredUpload matching query does not exist.'):
            self.delete_upload(test_id)

    def test_delete_stored_upload_local_no_filestore_path(self):
        fsp = local_settings.FILE_STORE_PATH
        local_settings.FILE_STORE_PATH = None
        # Need to set storage backend to None and make it reinitialise to
        # ensure that we're not using a remote backend for this test.
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False
        with self.assertRaisesMessage(
                ConfigurationError,
                'The file upload settings are not configured correctly.'):
            self.delete_upload(self.upload_id, delete_file=True)
        local_settings.FILE_STORE_PATH = fsp

    def test_delete_stored_upload_local_not_exists(self):
        # Need to set storage backend to None and make it reinitialise to
        # ensure that we're not using a remote backend for this test.
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False
        with patch('os.path.exists') as exists:
                with patch('os.path.isdir') as isdir:
                    exists.return_value = False
                    isdir.return_value = True
                    with self.assertRaisesMessage(
                            ConfigurationError,
                            ('The file upload settings are not configured '
                             'correctly.')):
                        self.delete_upload(self.upload_id, delete_file=True)

    def test_delete_stored_upload_local_not_isdir(self):
        # Need to set storage backend to None and make it reinitialise to
        # ensure that we're not using a remote backend for this test.
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False
        with patch('os.path.exists') as exists:
                with patch('os.path.isdir') as isdir:
                    exists.return_value = True
                    isdir.return_value = False
                    with self.assertRaisesMessage(
                            ConfigurationError,
                            ('The file upload settings are not configured '
                             'correctly.')):
                        self.delete_upload(self.upload_id, delete_file=True)

    def test_delete_stored_upload_remote_file_missing(self):
        self.mock_storage_backend.exists.return_value = False
        with self.assertRaisesMessage(
                FileNotFoundError,
                ('File [%s] for stored upload with id [%s] not found on '
                 'remote file store.'
                 % (self.test_target_filepath, self.upload_id))):
            self.delete_upload(self.upload_id, delete_file=True)

    def test_delete_stored_upload_local_file_missing(self):
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False
        target_filepath = os.path.join(
            local_settings.FILE_STORE_PATH, self.test_target_filepath)
        with patch('os.path.exists') as exists:
            exists.side_effect = [True, False]
            with self.assertRaisesMessage(
                    FileNotFoundError,
                    ('File [%s] to delete was not found on the local disk'
                     % (target_filepath))):
                self.delete_upload(self.upload_id, delete_file=True)

    def test_delete_stored_upload_local_remove_fails(self):
        # Make an API call to delete the stored upload and check that delete
        # is called on the FileSystemStorage backend.
        # Set the storage backend to None to force use of local storage.
        local_settings.STORAGES_BACKEND = None
        self.api.storage_backend_initialised = False

        # Get the target file path that we want to check that delete has been
        # called with. This is the file path from the DB plus the base file
        # system storage location.
        base_store_location = local_settings.FILE_STORE_PATH
        file_location = os.path.join(base_store_location,
                                     self.test_target_filepath)

        with patch('os.remove') as os_patcher:
            with patch('os.path.exists') as exists:
                with patch('os.path.isfile') as isfile:
                    exists.return_value = True
                    isfile.return_value = True
                    os_patcher.side_effect = OSError('Error deleting file')
                    with self.assertRaisesMessage(OSError,
                                                  'Error deleting file'):
                        self.delete_upload(self.upload_id, delete_file=True)
                    os_patcher.assert_called_once_with(file_location)

    def tearDown(self):
        local_settings.STORAGES_BACKEND = self.storage_backend

        self.su.delete()

        self.api.storage_backend_initialised = False
