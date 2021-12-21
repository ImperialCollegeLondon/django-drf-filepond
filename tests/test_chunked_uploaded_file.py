#############################################################################
#                                                                           #
#  Tests for DrfFilepondChunkedUploadedFile. These tests check the handling #
#  of chunked file uploads using the chunked uploaded file class which      #
#  provides a file interface over a set of file chunks stored on disk.      #
#                                                                           #
#############################################################################
from django_drf_filepond.utils import DrfFilepondChunkedUploadedFile
from django_drf_filepond.models import TemporaryUploadChunked
import logging

from django.test.testcases import TestCase

# Python 2/3 support
try:
    from unittest.mock import MagicMock, Mock, patch, call
except ImportError:
    from mock import MagicMock, Mock, patch, call

LOG = logging.getLogger(__name__)


#############################################################################
# Test the various capabilities and error conditions of the
# DrfFilepondChunkedUploadedFile class.
#
# test_chunked_upload_first_file_missing: We expect a FileNotFoundError if
#     we try to create a DrfFilepondChunkedUploadedFile instance when the
#     first chunk file is not present.
#
# test_chunked_upload_read_without_open: We expect an OSError if we try to
#     read from a DrfFilepondChunkedUploadedFile without calling open(mode)
#
# test_file_size_no_file: Check that we get an AttributeError if the
#     directory for the chunk files is missing.
#
# test_file_size_not_accessible: Check that we get an attribute error if
#     the getsize call fails on one of the file chunks.
#
# test_file_size_valid_files: Check that we can correctly calculate the
#     size of a set of (mocked) file chunks.
#
#############################################################################
class ChunkedUploadedFileTestCase(TestCase):

    def setUp(self):
        tuc = TemporaryUploadChunked()
        tuc.upload_id = 'EpqiJa5KFg8mbXryAPFVbC'
        tuc.file_id = 'MifCFREScUJH8ybrYwduoB'
        tuc.last_chunk = 13
        tuc.upload_dir = 'EpqiJa5KFg8mbXryAPFVbC'
        tuc.upload_complete = True
        tuc.upload_name = 'test_data.dat'
        tuc.total_size = 1048576
        self.tuc = tuc

        self.test_file_loc = '/test/location'

    def _setup_mocks(self, exists_val=False):
        # Mock out the "os" calls made when creating instance of chunked obj
        os = MagicMock()
        os.path = MagicMock()
        # Mocking the return of self.chunk_dir which is the join of
        # (storage.base_location (self.test_file_loc), tuc.upload_dir)
        # and self.first_file which is (self.chunk_dir, self.chunk_base + _1)
        # where self.chunk_base is tuc.file_id
        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        first_file = chunk_dir + '/' + self.tuc.file_id + '_1'
        os.path.join = Mock(side_effect=[chunk_dir, first_file])
        if type(exists_val) == list:
            os.path.exists = Mock(side_effect=exists_val)
        else:
            os.path.exists = Mock(return_value=exists_val)
        os.path.getsize = Mock(return_value=65536)
        storage = MagicMock()
        storage.base_location = self.test_file_loc
        return(os, storage, chunk_dir, first_file)

    def test_chunked_upload_first_file_missing(self):
        '''We expect a FileNotFoundError if we try to create a
           DrfFilepondChunkedUploadedFile instance when the first chunk
           file is not present.'''
        mock_os, mock_storage, chunk_dir, _ = self._setup_mocks()
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with self.assertRaisesRegex(
                        FileNotFoundError,
                        'Initial chunk for this file not found.'):
                    DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
        # Check the expected path was created/used when getting file location
        mock_os.path.join.assert_has_calls(
            [call(self.test_file_loc, self.tuc.upload_dir),
             call(chunk_dir, self.tuc.file_id + '_1')])
        mock_os.path.exists.assert_called_once_with(
            '%s/%s_1' % (chunk_dir, self.tuc.file_id))

    def test_chunked_upload_read_without_open(self):
        '''We expect an OSError if we try to read from a
           DrfFilepondChunkedUploadedFile without calling open(mode)'''
        mock_os, mock_storage, chunk_dir, _ = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with self.assertRaisesRegex(
                    OSError, ('File must be opened with "open\(mode\)" before '
                              'attempting to read data')):
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    for chunk in f.chunks():
                        pass
        # # Check the expected path was created/used when getting file location
        # mock_os.path.join.assert_has_calls(
        #     [call(self.test_file_loc, self.tuc.upload_dir),
        #      call(chunk_dir, self.tuc.file_id + '_1')])
        # mock_os.path.exists.assert_called_once_with(
        #     '%s/%s_1' % (chunk_dir, self.tuc.file_id))

    def test_file_size_no_file(self):
        '''Check that we get an AttributeError if the directory
           for the chunk files is missing.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            [True, False])
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                with self.assertRaises(
                        AttributeError,
                        msg='Unable to determine the file\'s size.'):
                    f.size

    def test_file_size_not_accessible(self):
        '''Check that we get an attribute error if the getsize call
           fails on one of the file chunks.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        mock_os.path.getsize = Mock(
            side_effect=[65536, OSError('Testing error getting size.')])
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                with self.assertRaisesRegex(
                    AttributeError, ('Unable to determine the file\'s size'
                                     ': Testing error getting size.')):
                    f.size

    def test_file_size_valid_files(self):
        '''Check that we can correctly calculate the size of a set of
           (mocked) file chunks.'''
        pass