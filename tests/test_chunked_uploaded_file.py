#############################################################################
#                                                                           #
#  Tests for DrfFilepondChunkedUploadedFile. These tests check the handling #
#  of chunked file uploads using the chunked uploaded file class which      #
#  provides a file interface over a set of file chunks stored on disk.      #
#                                                                           #
#############################################################################
import django_drf_filepond
from django_drf_filepond.exceptions import ChunkedUploadError
import logging
import os
from io import BytesIO, UnsupportedOperation

import django_drf_filepond.drf_filepond_settings as local_settings
from django.test.testcases import TestCase
from django_drf_filepond.models import TemporaryUploadChunked
from django_drf_filepond.utils import DrfFilepondChunkedUploadedFile

# Tests in this module require a version of mock that provides mock_open
# with support for a size parameter on it's returned readable object.
# We therefore use only the third party mock module (in place of unittest.
# mock) here since this is defined as a dependency in setup.py anyway.
from mock import MagicMock, Mock, call, mock_open, patch

# There's no built in FileNotFoundError in Python 2
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

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
# test_obj_first_file_not_exists_error: Test that we can't successfully
#     create a DrfFilepondChunkedUploadedFile object if the first file doesn't
#     exist
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
# test_chunks_read_chunk_larger_than_file: Check that when a chunk size is
#     specified on call to chunks() that is larger than the specified file
#     chunk size, that that this is handled successfully and used. This will
#     require reading from more than one file for each chunk yielded.
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
# test_chunks_read_full_data_same_chunk_size_incomplete_final: Test reading
#    of a set of multiple chunk "files" that are each the same size as the
#    chunk size, except for the final chunk which is less than the chunk
#    size - i.e. our test file is not an exact multiple of the chunk size.
#
# test_chunks_read_full_data_exact_chunk_multiple: Test reading of a set of
#     multiple chunk "files" that are each the same size as the chunk size.
#
# test_chunks_read_full_data_crossing_chunks: Test reading of a set of
#     multiple chunk "files" that are sized differently to the chunk size,
#     using a read chunk size that ensures we cross chunk file boundaries
#     during some reads. Check resulting read for equality with original
#     bytes.
#
# test_chunks_exact_chunk_multiple_empty_chunk: Due to the way that the
#     filepond client handles uploads, if the upload is an exact multiple
#     of the chunk size being used for uploads on the client side, the
#     final chunk will be empty. Test that this is handled correctly.
#
# test_chunks_not_enough_data_error: Check that when we have a set of chunk
#     files that don't contain enough data for the specified total file
#     size that a ChunkedUploadError is raised.
#
# test_chunks_not_enough_data_error_empty_files: Check that when we
#     have a set of chunks that don't contain enough data for the
#     specified total file size and that some of these files are empty,
#     a ChunkedUploadError is raised.
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

    def _setup_mocks(self, exists_val=False, join_list=None):
        # Mock out the "os" calls made when creating instance of chunked obj
        os = MagicMock()
        os.path = MagicMock()
        # Mocking the return of self.chunk_dir which is the join of
        # (storage.base_location (self.test_file_loc), tuc.upload_dir)
        # and self.first_file which is (self.chunk_dir, self.chunk_base + _1)
        # where self.chunk_base is tuc.file_id
        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        self.first_file = chunk_dir + '/' + self.tuc.file_id + '_1'
        if not join_list:
            os.path.join = Mock(side_effect=[chunk_dir] + [self.first_file]*5)
        else:
            os.path.join = Mock(side_effect=join_list)
        if type(exists_val) == list:
            os.path.exists = Mock(side_effect=exists_val)
        else:
            os.path.exists = Mock(return_value=exists_val)
        os.path.getsize = Mock(return_value=65536)
        storage = MagicMock()
        storage.base_location = self.test_file_loc
        return (os, storage, chunk_dir, self.first_file)

    def _init_file_tests(self, mock_data_info, exists_val=False):
        # Mock data info is a dict of filename: file_size for mock data
        default_data = (
            'ERROR: Got default data - expected filename not requested')
        mock_data = {}
        full_data = b''

        # The ordering of keys seems to be sorted in py3.6+ whereas
        # in 2.7/3.5 it isn't meaning that the full_data byte array is
        # generated in a different order to the way it's returned
        # via mock_open_se. To work around this, we sort the dict keys
        # in advance.
        mdi_keys = list(mock_data_info.keys())
        mdi_keys.sort()
        for key in mdi_keys:
            file_size = mock_data_info[key]
            file_data = os.urandom(file_size)
            full_data += file_data
            mock_data[key] = file_data

        def mock_open_se(fname, mode=None):
            mo = mock_open(read_data=mock_data.get(fname, default_data))()
            mo.closed = False
            mo.mode = 'rb'
            return mo

        return (mock_open_se, full_data)

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
                    OSError, (r'File must be opened with "open\(mode\)" '
                              r'before attempting to read data')):
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    for chunk in f.chunks():
                        pass

    def test_file_size_no_file(self):
        '''Check that we get an AttributeError if the directory
           for the chunk files is missing.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            [True, True, True, True, False])
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
        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)

        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            True, join_list=join_list)
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
        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)
        join_list += [chunk_file_base+str(i) for i in range(
            1, self.tuc.last_chunk + 1)]

        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            True, join_list=join_list)

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
                # Python 3 and 2.7 return different TypeError strings...
                with self.assertRaisesRegex(
                        TypeError,
                        (r'(open\(\) missing 1 required positional '
                         r'argument: \'mode\')|(open\(\) takes exactly'
                         r' 2 arguments \(1 given\))')):
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

    def test_obj_first_file_not_exists_error(self):
        '''Test that we can't successfully create a
           DrfFilepondChunkedUploadedFile object if the first file
           doesn't exit.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            [False])
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                with self.assertRaisesRegex(
                        FileNotFoundError,
                        'Initial chunk for this file not found.'):
                    DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')

    def test_file_open_chunk_and_offset_reset(self):
        '''Test that the chunk and offset are correctly reset to 1 and 0
           repsectively and open uses first chunk.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', mock_open()) as mo:
                with patch(utils_open_name, mock_open()) as mo:
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
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', mock_open()) as mo:
                with patch(utils_open_name, mock_open()) as mo:
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
        default_chunk_size = local_settings.TEMPFILE_READ_CHUNK_SIZE
        self._run_chunk_size_test(
            8388608, default_chunk_size, default_chunk_size)

    def test_chunks_specified_size_used(self):
        '''Check that when a chunk size is specified on call to chunks(),
           that that this is used.'''
        default_chunk_size = local_settings.TEMPFILE_READ_CHUNK_SIZE
        total_size = 8388608
        file_size = default_chunk_size
        read_chunk_size = 8192

        if (total_size % file_size) != 0:
            raise ValueError('The default chunk size must be a multiple of '
                             'the total size for the purpose of these tests.')
        num_chunks = total_size // file_size
        self.tuc.total_size = (file_size * num_chunks)
        self.tuc.last_chunk = num_chunks

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)

        mock_data_info = {}
        for i in range(1, num_chunks + 1):
            mock_data_info[chunk_file_base + str(i)] = file_size

        (mock_open_se, _) = self._init_file_tests(mock_data_info)

        mock_os, mock_storage, _, _ = self._setup_mocks(
            True, join_list=join_list)

        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    data = b''
                    i = 1
                    for c in f.chunks(chunk_size=read_chunk_size):
                        # Confirm that we read the expected default chunk size
                        self.assertEqual(read_chunk_size, len(c))
                        data += c
                        i += 1
                    f.close()

    def test_chunks_read_chunk_larger_than_file(self):
        '''Check that when a chunk size is specified on call to chunks() that
           is larger than the specified file chunk size, that that this is
           handled successfully and used. This will require reading from more
           than one file for each chunk yielded.'''
        self._run_chunk_size_test(8388608, 1048576, 2097152)

    def test_chunks_seek0_when_on_chunk_1(self):
        '''Check that when the current chunk is chunk 1 the read seeks to
           0 and resets the offset.'''
        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', mock_open()) as mo:
                with patch(utils_open_name, mock_open()) as mo:
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
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', mock_open()) as mo:
                with patch(utils_open_name, mock_open()) as mo:
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
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', mock_open()) as mo:
                with patch(utils_open_name, mock_open()) as mo:
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
        # Set up mock_open with data for this example
        # (based on https://bugs.python.org/issue38157)
        default_chunk_size = local_settings.TEMPFILE_READ_CHUNK_SIZE
        file_size = default_chunk_size // 2
        self.tuc.total_size = file_size
        self.tuc.last_chunk = 1

        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(True)
        mock_data_info = {first_file: file_size}
        (mock_open_se, _) = self._init_file_tests(mock_data_info)

        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', side_effect=mock_open_se) as mo:
                with patch(utils_open_name, side_effect=mock_open_se) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    data = b''
                    for c in f.chunks():
                        data += c
                    f.close()
        # Current chunk should be last chunk + 1
        self.assertEqual(f.current_chunk, 2)
        self.assertEqual(f.offset, file_size)
        mo.assert_called_once_with(self.first_file, 'rb')

    def test_chunks_read_full_data_same_chunk_size_incomplete_final(self):
        '''Test reading of a set of multiple chunk "files" that are each the
           same size as the chunk size, except for the final chunk which is
           less than the chunk size - i.e. our test file is not an exact
           multiple of the chunk size.'''
        chunk_file_size = local_settings.TEMPFILE_READ_CHUNK_SIZE
        last_file_size = chunk_file_size - 345
        self.tuc.total_size = (chunk_file_size * 8) + last_file_size
        self.tuc.last_chunk = 9

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        first_file = chunk_dir + '/' + self.tuc.file_id + '_1'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              first_file=first_file)

        (f, mo, _, _, _) = self._run_chunked_file_test(
            join_list, chunk_file_size, self.tuc.last_chunk, last_file_size)

        # Current chunk should be last chunk + 1 since we have a final file
        # that is sized such that it doesn't end exactly on a chunk boundary
        self.assertEqual(f.current_chunk, 10)
        self.assertEqual(f.offset, (chunk_file_size * 8) + last_file_size)
        mo.assert_has_calls([call(file_item, 'rb') for file_item in join_list[
            1:self.tuc.last_chunk]])

    def test_chunks_read_full_data_exact_chunk_multiple(self):
        '''Test reading of a set of multiple chunk "files" that are each the
           same size as the chunk size.'''
        chunk_file_size = local_settings.TEMPFILE_READ_CHUNK_SIZE
        last_file_size = chunk_file_size
        self.tuc.total_size = (chunk_file_size * 11)
        self.tuc.last_chunk = 11

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        first_file = chunk_dir + '/' + self.tuc.file_id + '_1'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              first_file=first_file)

        (f, mo, _, _, _) = self._run_chunked_file_test(
            join_list, chunk_file_size, self.tuc.last_chunk, last_file_size)

        # When the final chunk is smaller than the chunk size, current chunk
        # should be last chunk + 1 because the loop sees that it hasn't read
        # the full chunk size and increments the current chunk to see if
        # there's a file available with more data in the next chunk. When the
        # file is an exact multiple of the chunk size, we never enter the loop
        # to get more data after reading the final complete chunk so
        # current_chunk should equal the total number of chunks.
        self.assertEqual(f.current_chunk, 11)
        self.assertEqual(f.offset, (chunk_file_size * 11))
        mo.assert_has_calls([call(file_item, 'rb') for file_item in join_list[
            1:self.tuc.last_chunk]])

    def test_chunks_read_full_data_crossing_chunks(self):
        '''Test reading of a set of multiple chunk "files" that are sized
           differently to the chunk size, using a read chunk size that
           ensures we cross chunk file boundaries during some reads.
           Check resulting read for equality with original bytes.'''
        total_size = 234489
        file_size = 65536
        read_chunk_size = 2359

        last_file_size = total_size % file_size
        num_chunks = (total_size // file_size) + 1
        self.tuc.total_size = total_size
        self.tuc.last_chunk = num_chunks

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)

        (f, mo, iterations, data, full_data) = self._run_chunked_file_test(
            join_list, file_size, num_chunks, last_file_size, read_chunk_size)

        # Current chunk should be last chunk + 1
        self.assertEqual(f.current_chunk, num_chunks+1)
        self.assertEqual(f.offset, total_size)
        mo.assert_has_calls([call(file_item, 'rb') for file_item in join_list[
            1:self.tuc.last_chunk]])
        # Check that the number of read iterations is based on the
        # read_chunk_size and that the data read matches the original
        self.assertEqual(iterations, 100)
        arrays_equal = True
        b1 = BytesIO(data)
        b2 = BytesIO(full_data)
        for i in range(total_size):
            byte1 = b1.read(1)
            byte2 = b2.read(1)
            if byte1 != byte2:
                arrays_equal = False
        self.assertTrue(arrays_equal,
                        'Original byte array data is not equal to data read.')

    def test_chunks_exact_chunk_multiple_empty_chunk(self):
        '''Due to the way that the filepond client handles uploads, if the
           upload is an exact multiple of the chunk size being used for
           uploads on the client side, the final chunk will be empty. Test
           that this is handled correctly.'''

        # In reality, this situation shouldn't, in fact, occur. While the
        # filepond client does send an empty PATCH request at the end of
        # a set of chunks when the upload is an exact multiple of the
        # upload chunk size set in the configuration for the frontend client,
        # once django-drf-filepond detects that all bytes for a file have been
        # recieved, it assembles the chunks into the complete file.
        # The server code has been updated to accept the empty request when
        # this follows a completed temporary upload but an empty chunk file at
        # the end of the set of chunks is never actually stored.
        # Nonetheless, we check here that this case can still be handled.
        chunk_file_size = local_settings.TEMPFILE_READ_CHUNK_SIZE
        last_file_size = 0
        self.tuc.total_size = (chunk_file_size * 4)
        self.tuc.last_chunk = 5

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)

        (f, mo, iterations, data, full_data) = self._run_chunked_file_test(
            join_list, chunk_file_size, self.tuc.last_chunk, last_file_size)

        # Current chunk should be equal to the last chunk since the
        # file read is complete on the boundary of a chunk file.
        self.assertEqual(f.current_chunk, self.tuc.last_chunk - 1)
        self.assertEqual(f.offset, self.tuc.total_size)
        mo.assert_has_calls([call(file_item, 'rb') for file_item in join_list[
            1:self.tuc.last_chunk]])
        # Check that the number of read iterations is based on the
        # read_chunk_size and that the data read matches the original
        self.assertEqual(iterations, self.tuc.total_size // chunk_file_size)
        arrays_equal = True
        b1 = BytesIO(data)
        b2 = BytesIO(full_data)
        for i in range(self.tuc.total_size):
            byte1 = b1.read(1)
            byte2 = b2.read(1)
            if byte1 != byte2:
                arrays_equal = False
        self.assertTrue(arrays_equal,
                        'Original byte array data is not equal to data read.')

    def test_chunks_not_enough_data_error(self):
        '''Check that when we have a set of chunk files that don't contain
           enough data for the specified total file size that a
           ChunkedUploadError is raised.'''
        chunk_file_size = 1048576
        last_file_size = 65536
        self.tuc.total_size = (chunk_file_size * 4)
        self.tuc.last_chunk = 4

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)

        with self.assertRaisesRegex(
                ChunkedUploadError,
                ('No more data, read all chunks but expected file size <%s> '
                 'not reached - leaving loop at offset: %s'
                 % (self.tuc.total_size, str(65536*4)))):
            self._run_chunked_file_test(
                join_list, 65536, self.tuc.last_chunk, last_file_size)

    def test_chunks_not_enough_data_error_empty_files(self):
        '''Check that when we have a set of chunks that don't contain enough
           data for the specified total file size and that some of these
           files are empty, a ChunkedUploadError is raised.'''
        chunk_file_size = 1048576
        self.tuc.total_size = (chunk_file_size * 4)
        self.tuc.last_chunk = 8

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        join_list = self._get_chunk_join_list(chunk_dir, self.tuc.last_chunk,
                                              chunk_file_base=chunk_file_base)

        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            True, join_list=join_list)

        mock_data_info = {}
        mock_data_info[chunk_file_base + '1'] = chunk_file_size
        mock_data_info[chunk_file_base + '2'] = chunk_file_size
        mock_data_info[chunk_file_base + '8'] = chunk_file_size
        for i in range(3, 8):
            mock_data_info[chunk_file_base + str(i)] = 0

        (mock_open_se, full_data) = self._init_file_tests(mock_data_info)

        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    data = b''
                    with self.assertRaisesRegex(
                            ChunkedUploadError,
                            ('No more data, read all chunks but expected '
                             'file size <%s> not reached - leaving loop at '
                             'offset: %s' % (self.tuc.total_size,
                                             str(chunk_file_size*3)))):
                        try:
                            for c in f.chunks():
                                data += c
                        finally:
                            f.close()

    def _run_chunk_size_test(self, total_size, file_size, read_chunk_size):
        # Check that the file chunk size is a multiple of the total
        # size since that will simplify these tests
        if (total_size % file_size) != 0:
            raise ValueError('The default chunk size must be a multiple of '
                             'the total size for the purpose of these tests.')
        num_chunks = total_size // file_size
        self.tuc.total_size = (file_size * num_chunks)
        # Last chunk is incremented after each chunk is stored so it's
        # effectively a 1-indexed value defining the total number of chunks.
        # Chunk files are numbered from 1 too so last_chunk will be the
        # number at the end of the filename in the last chunk file.
        self.tuc.last_chunk = num_chunks

        chunk_dir = self.test_file_loc + '/' + self.tuc.upload_dir
        chunk_file_base = chunk_dir + '/' + self.tuc.file_id + '_'

        # This includes the chunk_dir for the initial os.path.join
        # call at utils.py:85, then we make another join call
        # at utils.py:92 to get the path to the first chunk file.
        # There's now an additional pre-check that all files are present
        # so that we don't start building the file and then subsequently
        # find a chunk is missing -utils.py:99-104. Finally we have stored
        # the path to the first file already but we again calculate the
        # paths to the other files in utils.py:192 which is why we add
        # paths 2 to n here again.
        join_list = [chunk_dir] + [
            chunk_file_base+str(i) for i in range(1, self.tuc.last_chunk + 1)
        ] + [
            chunk_file_base+str(i) for i in range(2, self.tuc.last_chunk + 1)]

        mock_data_info = {}
        for i in range(1, num_chunks + 1):
            mock_data_info[chunk_file_base + str(i)] = file_size

        (mock_open_se, _) = self._init_file_tests(mock_data_info)

        mock_os, mock_storage, _, _ = self._setup_mocks(
            True, join_list=join_list)

        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', side_effect=mock_open_se):
                with patch(utils_open_name, side_effect=mock_open_se):
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    data = b''
                    i = 1
                    for c in f.chunks(chunk_size=read_chunk_size):
                        LOG.debug('Read chunk %s, got <%s> bytes...'
                                  % (str(i), str(len(c))))
                        # Confirm that we read the expected default chunk size
                        self.assertEqual(read_chunk_size, len(c))
                        data += c
                        i += 1
                    f.close()

    def _run_chunked_file_test(self, join_list, chunk_size, num_chunks,
                               last_file_size, read_chunk_size=None):
        chunk_file_size = chunk_size

        mock_os, mock_storage, chunk_dir, first_file = self._setup_mocks(
            True, join_list=join_list)
        # Remove chunk number from first file
        chunk_file_base = first_file[:-1]
        mock_data_info = {}
        for i in range(1, num_chunks + 1):
            mock_data_info[chunk_file_base + str(i)] = (
                chunk_file_size if i != num_chunks else last_file_size)

        (mock_open_se, full_data) = self._init_file_tests(mock_data_info)

        iterations = 0

        with patch('django_drf_filepond.utils.os', mock_os):
            with patch('django_drf_filepond.utils.storage', mock_storage):
                utils_open_name = ('%s.open'
                                   % django_drf_filepond.utils.__name__)
                # with patch('builtins.open', side_effect=mock_open_se) as mo:
                with patch(utils_open_name, side_effect=mock_open_se) as mo:
                    f = DrfFilepondChunkedUploadedFile(
                        self.tuc, 'application/octet-stream')
                    self.assertEqual(f.first_file, self.first_file)
                    f.open('rb')
                    data = b''
                    if read_chunk_size:
                        for c in f.chunks(read_chunk_size):
                            data += c
                            iterations += 1
                    else:
                        for c in f.chunks():
                            data += c
                            iterations += 1
                    f.close()

        return (f, mo, iterations, data, full_data)

    ###
    # Prepare the list of file paths to be returned by the mocked
    # os.path.join calls in various tests.
    def _get_chunk_join_list(self, chunk_dir, last_chunk,
                             first_file=None, chunk_file_base=None):
        # This includes the chunk_dir for the initial os.path.join
        # call at utils.py:85, then we make another join call
        # at utils.py:92 to get the path to the first chunk file.
        # There's now an additional pre-check that all files are present
        # so that we don't start building the file and then subsequently
        # find a chunk is missing -utils.py:99-104. Finally we have stored
        # the path to the first file already but we again calculate the
        # paths to the other files in utils.py:192 which is why we add
        # paths 2 to n here again.
        if chunk_file_base:
            join_list = [chunk_dir] + [chunk_file_base+str(i) for i in range(
                1, self.tuc.last_chunk + 1)] + [
                    chunk_file_base+str(i) for i in range(
                        2, self.tuc.last_chunk + 1)]
        elif first_file:
            join_list = [chunk_dir] + [first_file[:-1]+str(i) for i in range(
                1, self.tuc.last_chunk + 1)] + [
                    first_file[:-1]+str(i) for i in range(
                        2, self.tuc.last_chunk + 1)]

        return join_list
