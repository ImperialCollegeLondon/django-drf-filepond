'''
Tests for the api functions provided by django-drf-filepond

store_upload:
    Stores a temporary upload to a path under the file store location which 
    is set using the DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting.
''' 
import logging
import os

from django.test import TestCase
from django_drf_filepond.api import store_upload
from django_drf_filepond.views import _get_file_id
from django.core.files.uploadedfile import SimpleUploadedFile
from django_drf_filepond.models import TemporaryUpload, StoredUpload

import django_drf_filepond.drf_filepond_settings as local_settings

LOG = logging.getLogger(__name__)

#########################################################################
# Tests for store_upload:
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
# test_store_upload_path_with_filename: Call store_upload with a valid ID 
#    and a path including a target filename which is different to the 
#    name of the file when originally uploaded.
#
# test_store_multiple_uploads_to_same_dir: Call store_upload twice with two 
#    different valid file storage IDs, using the same target directory but 
#    different filenames for each of the two uploads.
#
# test_store_upload_path_no_filename: Call store_upload with a valid ID and 
#    a directory path but no filename - the original name of the file 
#    when it was uploaded should be used and it should be placed into the 
#    specified location.
#
# test_store_upload_with_root_path: Call store_upload with the path set to 
#     '/'. The temporary upload should be stored in the root of the file 
#    store directory with the name originally provided when it was uploaded.
#
# test_store_upload_with_no_file_store_setting: Call store_upload with a  
#    valid upload_id but with no DJANGO_DRF_FILEPOND_FILE_STORE_PATH setting 
#    set in the application. This should raise an exception.
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
                  'are equal' % (test_target_filename, su.file_path))
        self.assertEqual(test_target_filename, su.file_path, 'File has ' 
                    'been stored with wrong filename in the database.')
        # Check that the file has actually been stored in the correct 
        # location and that the temporary file has been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None)
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')
        
        file_full_path = os.path.join(file_store_path, su.file_path)
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
        self.assertEqual(test_target_filename, su.file_path, 'File has ' 
                    'been stored with wrong filename in the database.')
        self.assertEqual(test_target_filename2, su2.file_path, 'File 2 has ' 
                    'been stored with wrong filename in the database.')
        
        # Check that the files have actually been stored in the correct 
        # locations and that the temporary files have been deleted
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        file_store_path = getattr(local_settings, 'FILE_STORE_PATH', None) 
        if not file_store_path:
            raise ValueError('Couldn\'t access file store path')
        
        file_full_path = os.path.join(file_store_path, su.file_path)
        file_full_path2 = os.path.join(file_store_path, su2.file_path)
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

    
    def tearDown(self):
        upload_tmp_base = getattr(local_settings, 'UPLOAD_TMP', None)
        filestore_base = getattr(local_settings, 'FILE_STORE_PATH', None)

        upload_tmp_dir = os.path.join(upload_tmp_base, self.upload_id)
        upload_tmp_file = os.path.join(upload_tmp_dir, self.fn)
        upload_tmp_dir2 = os.path.join(upload_tmp_base, self.upload_id2)
        upload_tmp_file2 = os.path.join(upload_tmp_dir2, self.fn)
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