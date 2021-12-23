#############################################################################
#                                                                           #
#  Tests for DrfFilepondChunkedUploadedFile. These tests check the handling #
#  of chunked file uploads using the chunked uploaded file class which      #
#  provides a file interface over a set of file chunks stored on disk.      #
#                                                                           #
#############################################################################
from io import UnsupportedOperation
from django_drf_filepond.utils import DrfFilepondChunkedUploadedFile
from django_drf_filepond.models import TemporaryUploadChunked
import logging

from django.test.testcases import TestCase

# Python 2/3 support
try:
    from unittest.mock import MagicMock, Mock, patch, call, mock_open
except ImportError:
    from mock import MagicMock, Mock, patch, call, mock_open

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
# test_multiple_chunks: Check that multiple_chunks() returns True
#     regardless of the chunk_size value specified.
#
# test_file_open_no_mode_error: Test that we can't open file without a mode
#
# test_file_open_no_first_file_error: Test that we can't successfully call
#     open on the file object if first_file (the pointer to the first chunk
#     file) is not specified.
#
# test_file_open_first_file_not_exists_error: Test that we can't
#     successfully call open on the file if first_file doesn't exist
#
# test_file_open_chunk_and_offset_reset: Test that the chunk and offset are
#     correctly reset to 1 and 0 repsectively and open uses first chunk.
#
# test_file_reopen_chunk_and_offset_reset: Test that chunk and offset are
#     reset to 1 and 0 repsectively and open uses first chunk on reopen.
#
# test_chunks_default_chunk_size: Check that when no chunk size is specified
#     on call to chunks(), that the default chunk size from settings is used.
#
# test_chunks_specified_size_used: Check that when a chunk size is specified
#     on call to chunks(), that that this is used.
#
# test_chunks_seek0_when_on_chunk_1: Check that when the current chunk is
#     chunk 1 the read seeks to 0 and resets the offset.
#
# test_chunks_seek_error: Check that an AttributeError and
#     UnsupportedOperation are handled when calling seek if chunks is called
#     when on chunk 1.
#
# test_chunks_reset_to_chunk_1_if_not_on_first_chunk: Check that when chunks
#     is called and we're not on chunk 1 that the offset and chunk are reset
#     and open is called on chunk 1s file.
#
# test_chunks_read_full_data_less_than_chunk_size: Read some data that has
#     a total size of less than chunk size.
#
# test_chunks_read_full_data_multiple_chunks: Test reading of a set of
#     multiple chunk "files" that are sized differently to the chunk size.
#
# test_chunks_read_full_data_exact_chunk_multiple: Test reading of a set of
#     multiple chunk "files" that are each the same size as the chunk size.
#
# test_chunks_read_full_data_crossing_chunks: Test reading of a set of
#     multiple chunk "files" that are sized differently to the chunk size,
#     using a read chunk size that ensures we cross chunk file boundaries
#     during some reads.
#
#############################################################################
class ChunkedUploadedFileTestCase(TestCase):

    def setUp(self):
        tuc = TemporaryUploadChunked()
        tuc.upload_id = 'EpqiJa5KFg8mbXryAPFVbC'
        tuc.file_id = 'MifCFREScUJH8ybrYwduoB'
        tuc.last_chunk = 4
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
        self.first_file = chunk_dir + '/' + self.tuc.file_id + '_1'
        os.path.join = Mock(side_effect=[chunk_dir] + [self.first_file]*5)
        if type(exists_val) == list:
            os.path.exists = Mock(side_effect=exists_val)
        else:
            os.path.exists = Mock(return_value=exists_val)
        os.path.getsize = Mock(return_value=65536)
        storage = MagicMock()
        storage.base_location = self.test_file_loc
        return(os, storage, chunk_dir, self.first_file)

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
        # There's a getsize call in the class init and then we let one succeed
        # in the size calculation look and the second will generate an OSError
        mock_os.path.getsize = Mock(
            side_effect=[65536, 65536, OSError('Testing error getting size.')])
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                with self.assertRaisesRegex(
                    AttributeError, ('Unable to get the file\'s size'
                                     ': Testing error getting size.')):
                    f.size

    def test_file_size_valid_files(self):
        '''Check that we can correctly calculate the size of a set of
           (mocked) file chunks.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        # There's a getsize call in the class init - set a different value for
        # this to avoid interference with the final calculated value.
        mock_os.path.getsize = Mock(
            side_effect=[10] + [65536]*4)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                fsize = f.size
        self.assertEqual(fsize, 65536*4,
                         msg='Got incorrect size for file chunks.')

    def test_multiple_chunks(self):
        '''Check that multiple_chunks() returns True regardless of
           the chunk_size value specified.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                self.assertTrue(f.multiple_chunks(),
                                msg='Multiple chunks should always be True')
                self.assertTrue(f.multiple_chunks(1024),
                                msg='Multiple chunks should always be True')
                self.assertTrue(f.multiple_chunks(chunk_size=2048),
                                msg='Multiple chunks should always be True')
                self.assertTrue(f.multiple_chunks(chunk_size=4294967296),
                                msg='Multiple chunks should always be True')

    def test_file_open_no_mode_error(self):
        '''Test that we can't open file without a mode'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                with self.assertRaisesRegex(
                    TypeError, (r'open\(\) missing 1 required positional '
                                'argument: \'mode\'')):
                    f.open()

    def test_file_open_no_first_file_error(self):
        '''Test that we can't successfully call open on the file object if
           first_file (the pointer to the first chunk file) is not
           specified.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                f.first_file = None
                with self.assertRaisesRegex(
                        ValueError, 'The file cannot be reopened.'):
                    f.open('rb')

    def test_file_open_first_file_not_exists_error(self):
        '''Test that we can't successfully call open on the file if
           first_file doesn't exist'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            [True, False])
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                f = DrfFilepondChunkedUploadedFile(
                    self.tuc, 'application/octet-stream')
                self.assertEqual(f.first_file, self.first_file)
                with self.assertRaisesRegex(
                        ValueError, 'The file cannot be reopened.'):
                    f.open('rb')

    def test_file_open_chunk_and_offset_reset(self):
        '''Test that the chunk and offset are correctly reset to 1 and 0
           repsectively and open uses first chunk.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with patch('builtins.open', mock_open()) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    f.current_chunk = 12
                    f.offset = 1048576
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
        self.assertEqual(f.current_chunk, 1)
        self.assertEqual(f.offset, 0)
        mo.assert_called_with(self.first_file, 'rb')

    def test_file_reopen_chunk_and_offset_reset(self):
        '''Test that chunk and offset are reset to 1 and 0 repsectively and
           open uses first chunk on reopen.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with patch('builtins.open', mock_open()) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    f.current_chunk = 12
                    f.offset = 1048576
                    self.assertFalse(f.file.close.called)
                    f.file.closed = False
                    # Attempt re-open
                    f.open('rb')
        self.assertEqual(f.current_chunk, 1)
        self.assertEqual(f.offset, 0)
        self.assertTrue(f.file.close.called)
        mo.assert_called_with(self.first_file, 'rb')

    def test_chunks_default_chunk_size(self):
        '''Check that when no chunk size is specified on call to chunks(),
           that the default chunk size from settings is used.'''
        raise NotImplementedError('This test is not yet implemented.')

    def test_chunks_specified_size_used(self):
        '''Check that when a chunk size is specified on call to chunks(),
           that that this is used.'''
        raise NotImplementedError('This test is not yet implemented.')

    def test_chunks_seek0_when_on_chunk_1(self):
        '''Check that when the current chunk is chunk 1 the read seeks to
           0 and resets the offset.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with patch('builtins.open', mock_open()) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    f.current_chunk = 1
                    f.offset = 2048
                    f.file.closed = False
                    # Set total size to 0 so we don't enter chunk read loop
                    f.total_size = 0
                    for c in f.chunks():
                        pass
        f.file.seek.assert_called_with(0)
        self.assertEqual(f.current_chunk, 1)
        self.assertEqual(f.offset, 0)
        mo.assert_called_once_with(self.first_file, 'rb')

    def test_chunks_seek_error(self):
        '''Check that an AttributeError and UnsupportedOperation are handled
           when calling seek if chunks is called when on chunk 1.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with patch('builtins.open', mock_open()) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    f.current_chunk = 1
                    f.offset = 2048
                    f.file.closed = False
                    # Set total size to 0 so we don't enter chunk read loop
                    f.total_size = 0
                    # Set offset to non-0 so we can check that the error was
                    # raised (the call to set offset to 0 is after seek)
                    f.offset = 10
                    f.file.seek = Mock(side_effect=AttributeError())
                    for c in f.chunks():
                        pass
                    self.assertEqual(f.offset, 10)
                    # Now run the same check with UnsupportedOperation
                    f.offset = 20
                    f.file.seek = Mock(side_effect=UnsupportedOperation())
                    for c in f.chunks():
                        pass
                    self.assertEqual(f.offset, 20)
        mo.assert_called_once_with(self.first_file, 'rb')

    def test_chunks_reset_to_chunk_1_if_not_on_first_chunk(self):
        '''Check that when chunks is called and we're not on chunk 1 that the
           offset and chunk are reset and open is called on chunk 1s file.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with patch('builtins.open', mock_open()) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    f.current_chunk = 10
                    f.offset = 2048
                    f.file.closed = False
                    # Set total size to 0 so we don't enter chunk read loop
                    f.total_size = 0
                    for c in f.chunks():
                        pass
        self.assertFalse(f.file.seek.called)
        self.assertEqual(f.current_chunk, 1)
        self.assertEqual(f.offset, 0)
        mo.assert_called_with(self.first_file, 'rb')

    def test_chunks_read_full_data_less_than_chunk_size(self):
        '''Read some data that has a total size of less than chunk size.'''
        raise NotImplementedError('This test is not yet implemented.')

    def test_chunks_read_full_data_multiple_chunks(self):
        '''Test reading of a set of multiple chunk "files" that are sized
           differently to the chunk size.'''
        raise NotImplementedError('This test is not yet implemented.')

    def test_chunks_read_full_data_exact_chunk_multiple(self):
        '''Test reading of a set of multiple chunk "files" that are each the
           same size as the chunk size.'''
        raise NotImplementedError('This test is not yet implemented.')

    def test_chunks_read_full_data_crossing_chunks(self):
        '''Test reading of a set of multiple chunk "files" that are sized
           differently to the chunk size, using a read chunk size that
           ensures we cross chunk file boundaries during some reads.'''
        raise NotImplementedError('This test is not yet implemented.')
