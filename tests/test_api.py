'''
Tests for the store_upload api function provided by django-drf-filepond

THIS SET OF TESTS WILL TEST LOCAL STORAGE FUNCTIONALITY OF THE store_upload
FUNCTION.

store_upload:
    Moves a temporary upload to permanent storage at a location on the local
    filesystem or to a remote file store via the django-storages library.
    If using a local filestore, the base location where files are stored is
    set using the DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting. If using a
    remote file store, this setting defines the base location on the remote
    file store where files will placed.
'''
import logging
import os

from django.test import TestCase
from django_drf_filepond.api import store_upload
from django_drf_filepond.views import _get_file_id
from django.core.files.uploadedfile import SimpleUploadedFile
from django_drf_filepond.models import TemporaryUpload, StoredUpload

import django_drf_filepond.drf_filepond_settings as local_settings
from django.core.exceptions import ImproperlyConfigured
from django_drf_filepond.api import _store_upload_local

# There's no built in FileNotFoundError, FileExistsError in Python 2
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

try:
    FileExistsError
except NameError:
    FileExistsError = OSError

# Python 2/3 support
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

LOG = logging.getLogger(__name__)


#########################################################################
# Tests for store_upload:
#
# test_store_upload_unset_file_store_path: Call store_upload with the file
#    store path in settings unset. An exception should be raised.
#
# test_store_upload_invalid_id: Call store_upload with an invalid ID that
#    doesn't fit the required ID format.
#
# test_store_upload_invalid_id_correct_format: Call store_upload with an
#    invalid ID that is of the correct format.
#
# test_store_upload_path_none: Call store_upload with a valid ID but path
#    set to none.
#
# test_store_upload_path_blank: Call store_upload with a valid ID but path
#    set to empty string.
#
# test_store_upload_path_with_dirname: Call store_upload with a valid ID
#    and a path which is a directory (with a leading slash) but no target
#    filename. The file should end up in the specified location,
#    relative to the configured FILE_STORE_PATH, with the file named using
#    the original name of the file when it was uploaded.
#
# test_store_upload_path_with_dirname_no_leading_sep: Call store_upload with
#    a valid ID and a path including a target location which is a directory
#    (with a leading file separator). The file should end up in the specified
#     location, relative to the configured FILE_STORE_PATH.
#
# test_store_upload_path_with_filename: Call store_upload with a valid ID
#    and a path including a target filename which is different to the
#    name of the file when originally uploaded.
#
# test_store_multiple_uploads_to_same_dir: Call store_upload twice with two
#    different valid file storage IDs, using the same target directory but
#    different filenames for each of the two uploads.
#
# test_store_upload_with_root_path: Call store_upload with the path set to
#     '/'. The temporary upload should be stored in the root of the file
#    store directory with the name originally provided when it was uploaded.
#
# test_store_upload_local_direct_file_exists: Call _store_upload_local with
#    a target file that already exists. Expect a FileExistsError
#
# test_store_upload_local_direct_no_file_store_path: Call store_upload with
#    the file store path in settings unset. An exception should be raised.
#
# test_store_upload_local_direct_missing_store_path: Call _store_upload_local
#    with a file store directory set that is missing. Expect exception.
#
# test_store_upload_local_copy_to_store_fails: Call _store_upload_local and
#    the copy to permanent storage fails - expect exception.
#
class ApiTestCase(TestCase):

    def setUp(self):
        # Set up an initial file upload
        self.upload_id = _get_file_id()
        self.upload_id2 = _get_file_id()
        self.file_id = _get_file_id()
        self.file_content = ('This is some test file data for an '
                             'uploaded file.')
        self.fn = 'my_test_file.txt'
        self.test_target_dirname = 'test_storage/'
        self.test_target_filename = '/test_storage/testfile.txt'
        self.test_target_filename2 = '/test_storage/testfile2.txt'
        uploaded_file = SimpleUploadedFile(self.fn,
                                           str.encode(self.file_content))
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

    def test_store_upload_unset_file_store_path(self):
        fsp = local_settings.FILE_STORE_PATH
        local_settings.FILE_STORE_PATH = None
        with self.assertRaisesMessage(
                ImproperlyConfigured, 'A required setting is missing in '
                'your application configuration.'):
            store_upload('hsdfiuysh78sdhiu', '/test_storage/test_file.txt')
        local_settings.FILE_STORE_PATH = fsp

    def test_store_upload_invalid_id(self):
        with self.assertRaisesMessage(ValueError, 'The provided upload ID '
                                      'is of an invalid format.'):
            store_upload('hsdfiuysh78sdhiu', '/test_storage/test_file.txt')

#         tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
#         store_upload(self.upload_id, '/test_storage/%s' % tu.uplod_name)

    def test_store_upload_invalid_id_correct_format(self):
        with self.assertRaisesMessage(ValueError, 'Record for the specified '
                                      'upload_id doesn\'t exist'):
            store_upload('hsdfiuysh78sdhiuf73gds', '/test_storage/test.txt')

    def test_store_upload_path_none(self):
        with self.assertRaisesMessage(ValueError,  'No destination file '
                                      'path provided.'):
            store_upload('hsdfiuysh78sdhiuf73gds', None)

    def test_store_upload_path_blank(self):
        with self.assertRaisesMessage(ValueError, 'No destination file '
                                      'path provided.'):
            store_upload('hsdfiuysh78sdhiuf73gds', '')

    def test_store_upload_path_with_filename(self):
        test_target_filename = self.test_target_filename
        if test_target_filename.startswith(os.sep):
            test_target_filename = test_target_filename[1:]
        su = store_upload(self.upload_id, test_target_filename)
        upload_id = su.upload_id
        su = StoredUpload.objects.get(upload_id=upload_id)
        LOG.debug('About to check that file path <%s> and stored path <%s> '
                  'are equal' % (test_target_filename, su.file.name))
        self.assertEqual(
            test_target_filename, su.file.name,
            'File has been stored with wrong filename in the database.')
        # Check that the file has actually been stored in the correct
        # location and that the temporary file has been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')

        file_full_path = os.path.join(file_store_path, su.file.name)
        self.assertTrue(os.path.exists(file_full_path) and
                        os.path.isfile(file_full_path))
        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id, self.file_id)))

    def test_store_upload_with_root_path(self):
        test_target_dirname = '/'
        su = store_upload(self.upload_id, test_target_dirname)
        upload_id = su.upload_id
        su = StoredUpload.objects.get(upload_id=upload_id)
        target_file_path = os.path.join(test_target_dirname, self.fn)
        LOG.debug('About to check that file path <%s> and stored path <%s> '
                  'are equal' % (target_file_path, su.file.name))
        self.assertEqual(
            target_file_path[1:], su.file.name,
            'File has been stored with wrong filename in the database.')
        # Check that the file has actually been stored in the correct
        # location and that the temporary file has been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')

        file_full_path = os.path.join(file_store_path, su.file.name)
        self.assertTrue(os.path.exists(file_full_path) and
                        os.path.isfile(file_full_path))
        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id, self.file_id)))

    def test_store_upload_path_with_dirname(self):
        test_target_dirname = self.test_target_dirname
        if test_target_dirname.startswith(os.sep):
            test_target_dirname = test_target_dirname[1:]
        su = store_upload(self.upload_id, test_target_dirname)
        upload_id = su.upload_id
        su = StoredUpload.objects.get(upload_id=upload_id)
        target_file_path = os.path.join(test_target_dirname, self.fn)
        LOG.debug('About to check that file path <%s> and stored path <%s> '
                  'are equal' % (target_file_path, su.file.name))
        self.assertEqual(
            target_file_path, su.file.name,
            'File has been stored with wrong filename in the database.')
        # Check that the file has actually been stored in the correct
        # location and that the temporary file has been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')

        file_full_path = os.path.join(file_store_path, su.file.name)
        self.assertTrue(os.path.exists(file_full_path) and
                        os.path.isfile(file_full_path))
        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id, self.file_id)))

    def test_store_upload_path_with_dirname_no_leading_sep(self):
        test_target_dirname = self.test_target_dirname
        if not test_target_dirname.startswith(os.sep):
            test_target_dirname = os.sep + test_target_dirname
        su = store_upload(self.upload_id, test_target_dirname)
        upload_id = su.upload_id
        # File should be stored relative to the file store path so the
        # leading os.sep should be ignored.
        su = StoredUpload.objects.get(upload_id=upload_id)
        target_file_path = os.path.join(test_target_dirname, self.fn)
        if target_file_path.startswith(os.sep):
            target_file_path = target_file_path[1:]
        LOG.debug('About to check that file path <%s> and stored path <%s> '
                  'are equal' % (target_file_path, su.file.name))
        self.assertEqual(
            target_file_path, su.file.name,
            'File has been stored with wrong filename in the database.')
        # Check that the file has actually been stored in the correct
        # location and that the temporary file has been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')

        file_full_path = os.path.join(file_store_path, su.file.name)
        self.assertTrue(os.path.exists(file_full_path) and
                        os.path.isfile(file_full_path))
        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id, self.file_id)))

    def test_store_multiple_uploads_to_same_dir(self):
        test_target_filename = self.test_target_filename
        test_target_filename2 = self.test_target_filename2
        if test_target_filename.startswith(os.sep):
            test_target_filename = test_target_filename[1:]
        if test_target_filename2.startswith(os.sep):
            test_target_filename2 = test_target_filename2[1:]

        su = store_upload(self.upload_id, test_target_filename)
        su2 = store_upload(self.upload_id2, test_target_filename2)
        self.assertEqual(
            test_target_filename, su.file.name,
            'File has been stored with wrong filename in the database.')
        self.assertEqual(
            test_target_filename2, su2.file.name,
            'File 2 has been stored with wrong filename in the database.')

        # Check that the files have actually been stored in the correct
        # locations and that the temporary files have been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')

        file_full_path = os.path.join(file_store_path, su.file.name)
        file_full_path2 = os.path.join(file_store_path, su2.file.name)
        # Check first file
        self.assertTrue(os.path.exists(file_full_path) and
                        os.path.isfile(file_full_path))
        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id, self.file_id)))
        # Check second file
        self.assertTrue(os.path.exists(file_full_path2) and
                        os.path.isfile(file_full_path2))
        self.assertFalse(os.path.exists(
            os.path.join(upload_tmp_base, self.upload_id2, self.file_id)))

    def test_store_upload_local_direct_no_file_store_path(self):
        fsp = local_settings.FILE_STORE_PATH
        local_settings.FILE_STORE_PATH = None
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        with self.assertRaisesMessage(
                ValueError,
                'The FILE_STORE_PATH is not set to a directory.'):
            _store_upload_local('/test_storage', 'test_file.txt', tu)
        local_settings.FILE_STORE_PATH = fsp

    def test_store_upload_local_direct_missing_store_path(self):
        fsp = local_settings.FILE_STORE_PATH
        test_dir = '/tmp/%s' % _get_file_id()
        local_settings.FILE_STORE_PATH = test_dir
        with self.assertRaisesMessage(
                FileNotFoundError,
                'The local output directory [%s] defined by '
                'FILE_STORE_PATH is missing.' % test_dir):
            _store_upload_local('/test_storage', 'test_file.txt', None)
        local_settings.FILE_STORE_PATH = fsp

    def test_store_upload_local_direct_file_exists(self):
        filestore_base = getattr(local_settings, 'FILE_STORE_PATH', None)
        target_file_dir = os.path.join(filestore_base, 'test_storage')
        os.mkdir(target_file_dir)
        with open(os.path.join(target_file_dir, 'testfile.txt'), 'a') as f:
            f.write('\n')
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        with self.assertRaisesMessage(
                FileExistsError,
                'The specified temporary file cannot be stored to the '
                'specified location - file exists.'):
            _store_upload_local('/test_storage', 'testfile.txt', tu)

    def test_store_upload_local_copy_to_store_fails(self):
        tu = TemporaryUpload.objects.get(upload_id=self.upload_id)
        with patch('shutil.copy2') as copy2_patch:
            with patch('os.path.exists') as exists_patch:
                with patch('os.path.isdir') as isdir_patch:
                    exists_patch.side_effect = [True, False, True]
                    isdir_patch.return_value = True
                    copy2_patch.side_effect = IOError(
                        'Error moving temporary file to permanent storage '
                        'location')
                    with self.assertRaisesMessage(
                            IOError,
                            'Error moving temporary file to permanent '
                            'storage location'):
                        _store_upload_local('/test_storage', 'testfile.txt',
                                            tu)

    def tearDown(self):
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        filestore_base = getattr(local_settings, 'FILE_STORE_PATH', None)

        upload_tmp_dir = os.path.join(upload_tmp_base, self.upload_id)
        upload_tmp_dir2 = os.path.join(upload_tmp_base, self.upload_id2)
        tmp_files = [(upload_tmp_dir, self.fn), (upload_tmp_dir2, self.fn)]

        test_filename = self.test_target_filename
        test_filename2 = self.test_target_filename2
        test_dirname = self.test_target_dirname
        if test_filename.startswith(os.sep):
            test_filename = test_filename[1:]
        if test_filename2.startswith(os.sep):
            test_filename2 = test_filename2[1:]
        if test_dirname.startswith(os.sep):
            test_dirname = test_dirname[1:]

        test_filename_fn = os.path.join(test_dirname, self.fn)

        test_target_file = os.path.join(filestore_base, test_filename)
        test_target_file2 = os.path.join(filestore_base, test_filename2)
        test_target_dir_fn = os.path.join(filestore_base, test_filename_fn)
        test_target_file_fn = os.path.join(filestore_base, self.fn)
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
        # If a test was run using only the target directory as the file
        # target then the file will be stored with self.fn since no target
        # filename has been specified, need to check for this case too
        if (os.path.exists(test_target_file_fn) and
                os.path.isfile(test_target_file_fn)):
            LOG.debug('Removing test_target_file_fn:<%s>'
                      % test_target_file_fn)
            os.remove(test_target_file_fn)
        if (os.path.exists(test_target_dir_fn) and
                os.path.isfile(test_target_dir_fn)):
            LOG.debug('Removing test_target_dir_fn:<%s>'
                      % test_target_dir_fn)
            os.remove(test_target_dir_fn)
        # Remove directory
        if (os.path.exists(test_target_dir) and
                os.path.isdir(test_target_dir)):
            LOG.debug('Removing test target dir: <%s>' % test_target_dir)
            os.rmdir(test_target_dir)
