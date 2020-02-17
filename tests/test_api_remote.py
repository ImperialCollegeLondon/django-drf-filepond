'''
Tests for the store_upload api function provided by django-drf-filepond

THIS SET OF TESTS WILL TEST REMOTE STORAGE FUNCTIONALITY OF THE store_upload
FUNCTION.

store_upload:
    Moves a temporary upload to permanent storage at a location on the local
    filesystem or to a remote file store via the django-storages library.
    If using a local filestore, the base location where files are stored is
    set using the DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting. If using a
    remote file store, the settings for the storage backend determine the
    base file storage location relative to which files will be placed.
'''
import logging
import os

from django.test import TestCase
from django_drf_filepond.views import _get_file_id
from django.core.files.uploadedfile import SimpleUploadedFile
from django_drf_filepond.models import TemporaryUpload, StoredUpload

import django_drf_filepond.drf_filepond_settings as local_settings

# Python 2/3 support
try:
    from unittest.mock import MagicMock
    from unittest.mock import patch
except ImportError:
    from mock import MagicMock
    from mock import patch

store_upload = None

LOG = logging.getLogger(__name__)


#########################################################################
# Tests for remote storage using store_upload:
#
# test_remote_store_upload_invalid_id: Call store_upload with an invalid ID
#    that doesn't fit the required ID format.
#
# test_remote_store_upload_invalid_id_correct_format: Call store_upload with
#    an invalid ID that is of the correct format.
#
# test_remote_store_upload_path_none: Call store_upload with a valid ID but
#    path set to none.
#
# test_remote_store_upload_path_blank: Call store_upload with a valid ID but
#    path set to empty string.
#
# test_remote_store_upload_path_with_filename: Call store_upload with a valid
#    ID and a path including a target filename which is different to the
#    name of the file when originally uploaded.
#
# test_remote_store_multiple_uploads_to_same_dir: Call store_upload twice
#    with two different valid file storage IDs, using the same target
#    directory but different filenames for each of the two uploads.
#
# test_remote_store_upload_path_no_filename: Call store_upload with a valid
#    ID and a directory path but no filename - the original name of the file
#    when it was uploaded should be used and it should be placed into the
#    specified location.
#
# test_remote_store_upload_with_root_path: Call store_upload with the path
#     set to '/'. The temporary upload should be stored in the root of the
#    file store directory with the name originally provided when it was
#    uploaded.
#
# test_remote_store_upload_with_no_file_store_setting: Call store_upload with
#    a valid upload_id but with no DJANGO_DRF_FILEPOND_FILE_STORE_PATH
#    setting set in the application. This should raise an exception.
#
# test_remote_store_upload_fails: Call _remote_store_upload and cause save
#    on the storage backend to fail, checking that an exception is raised.
#
# test_remote_store_upload_uses_tu_filename: Call _remote_store_upload and
#    check that if no filename is provided, the name from temp_upload is used.
#
class ApiRemoteTestCase(TestCase):

    def setUp(self):
        global store_upload
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
        store_upload = django_drf_filepond.api.store_upload

        # Check that we're using a mocked storage backend
        self.assertTrue(
            isinstance(django_drf_filepond.api.storage_backend, MagicMock),
            ('The created storage backend should be mocked but it is not of '
             'type unittest.mock.MagicMock...'))

        # Set up an initial file upload
        self.upload_id = _get_file_id()
        self.upload_id2 = _get_file_id()
        self.file_id = _get_file_id()
        self.file_content = ('This is some test file data for an '
                             'uploaded file.')
        self.fn = 'my_test_file.txt'
        self.test_target_filename = '/test_storage/testfile.txt'
        self.test_target_filename2 = '/test_storage/testfile2.txt'
        uploaded_file = MagicMock(spec=SimpleUploadedFile)
        uploaded_file.name = self.fn
        tu = TemporaryUpload(upload_id=self.upload_id,
                             file_id=self.file_id,
                             file=uploaded_file, upload_name=self.fn,
                             upload_type=TemporaryUpload.FILE_DATA)
        tu.save()

        tu2 = TemporaryUpload(upload_id=self.upload_id2,
                              file_id=self.file_id,
                              file=uploaded_file, upload_name=self.fn,
                              upload_type=TemporaryUpload.FILE_DATA)
        tu2.save()

    def test_remote_store_upload_invalid_id(self):
        with self.assertRaisesMessage(ValueError, 'The provided upload ID '
                                      'is of an invalid format.'):
            store_upload('hsdfiuysh78sdhiu', '/test_storage/test_file.txt')

    def test_remote_store_upload_invalid_id_correct_format(self):
        with self.assertRaisesMessage(ValueError, 'Record for the specified '
                                      'upload_id doesn\'t exist'):
            store_upload('hsdfiuysh78sdhiuf73gds', '/test_storage/test.txt')

    def test_remote_store_upload_path_none(self):
        with self.assertRaisesMessage(ValueError,  'No destination file '
                                      'path provided.'):
            store_upload('hsdfiuysh78sdhiuf73gds', None)

    def test_remote_store_upload_path_blank(self):
        with self.assertRaisesMessage(ValueError, 'No destination file '
                                      'path provided.'):
            store_upload('hsdfiuysh78sdhiuf73gds', '')

    def test_remote_store_upload_path_with_filename(self):
        test_target_filename = self.test_target_filename
        if test_target_filename.startswith(os.sep):
            test_target_filename = test_target_filename[1:]
        su = store_upload(self.upload_id, test_target_filename)

        mock_fieldfile = MagicMock(
            spec='django.db.models.fields.files.FieldFile')
        mock_fieldfile.name = os.path.join(self.upload_id, self.fn)
        # Check that our mock storage backend had the correct function
        # called with the correct parameters
        self.mock_storage_backend.save.assert_called_once_with(
            test_target_filename, mock_fieldfile)

        upload_id = su.upload_id
        su = StoredUpload.objects.get(upload_id=upload_id)
        LOG.debug('About to check that file path <%s> and stored path <%s> '
                  'are equal' % (test_target_filename, su.file.name))
        self.assertEqual(
            test_target_filename, su.file.name,
            'File has been stored with wrong filename in the database.')

        # In the local check, we can check here that the file has actually
        # been stored at the correct location. Here we can't do this because
        # the file may have been stored remotely. However, we check that any
        # temporary file that was created has been removed.
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)

        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id, self.file_id)))

    def test_remote_store_upload_fails(self):
        errorMsg = 'Error saving file to remote storage backend.'
        self.mock_storage_backend.save.side_effect = Exception(errorMsg)

        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        with self.assertRaisesMessage(Exception, errorMsg):
            self.api._store_upload_remote('', self.fn, tu)

    def test_remote_store_upload_uses_tu_filename(self):
        errorMsg = 'Throwing error to prevent further running during test.'
        self.mock_storage_backend.save.side_effect = Exception(errorMsg)
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        with self.assertRaisesMessage(Exception, errorMsg):
            self.api._store_upload_remote('/test_storage/', None, tu)
        self.mock_storage_backend.save.assert_called_once_with(
            os.path.join('/test_storage/', tu.upload_name), tu.file)

    def tearDown(self):
        # self.patcher.stop() # Not required, done via cleanup hook
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        filestore_base = getattr(local_settings, 'FILE_STORE_PATH', None)

        upload_tmp_dir = os.path.join(upload_tmp_base, self.upload_id)
        upload_tmp_dir2 = os.path.join(upload_tmp_base, self.upload_id2)
        tmp_files = [(upload_tmp_dir, self.fn), (upload_tmp_dir2, self.fn)]

        test_filename = self.test_target_filename
        test_filename2 = self.test_target_filename2
        if test_filename.startswith(os.sep):
            test_filename = test_filename[1:]
        if test_filename2.startswith(os.sep):
            test_filename2 = test_filename2[1:]

        test_target_file = os.path.join(filestore_base, test_filename)
        test_target_file2 = os.path.join(filestore_base, test_filename2)
        test_target_dir = os.path.dirname(test_target_file)

        for tmp_file in tmp_files:
            tmp_file_path = os.path.join(tmp_file[0], tmp_file[1])
            if (os.path.exists(tmp_file_path) and
                    os.path.isfile(tmp_file_path)):
                LOG.debug('Removing temporary file: <%s>' % tmp_file_path)
                os.remove(tmp_file_path)
            if (os.path.exists(tmp_file[0]) and os.path.isdir(tmp_file[0])):
                LOG.debug('Removing temporary dir: <%s>' % tmp_file[0])
                os.rmdir(tmp_file[0])

        # Remove test_target_file
        if (os.path.exists(test_target_file) and
                os.path.isfile(test_target_file)):
            LOG.debug('Removing test target file: <%s>' % test_target_file)
            os.remove(test_target_file)
        if (os.path.exists(test_target_file2) and
                os.path.isfile(test_target_file2)):
            LOG.debug('Removing test target file 2:<%s>' % test_target_file2)
            os.remove(test_target_file2)
        if (os.path.exists(test_target_dir) and
                os.path.isdir(test_target_dir)):
            LOG.debug('Removing test target dir: <%s>' % test_target_dir)
            os.rmdir(test_target_dir)
