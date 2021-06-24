import logging
import re

from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase
from rest_framework.request import Request
import shortuuid
from six import text_type

import django_drf_filepond.drf_filepond_settings as local_settings
from django_drf_filepond.utils import _get_user, _get_file_id, \
    get_local_settings_base_dir


# Python 2/3 support
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

LOG = logging.getLogger(__name__)


# test_get_user_regular: Test that _get_user correctly extracts a request user
#
# test_get_user_anonymous: Test that _get_user correctly handles an anonymous
#    request user.
#
# test_get_file_id: Test that get_file_id returns an ID that corresponds to
#    the 22-character specification.
#
# test_get_base_dir_with_str: Test that when the local settings BASE_DIR
#    is a string, a string is returned.
#
# test_get_base_dir_with_path: Test that when the local settings BASE_DIR
#    is a Path object, a string is returned.
#
# test_get_base_dir_join_path: Test that when the local settings BASE_DIR
#    is a Path object, a string is returned.
#
class UtilsTestCase(TestCase):

    def test_get_user_regular(self):
        req = MagicMock(spec=Request)
        req.user = User(username='test_user')
        u = _get_user(req)
        self.assertEqual(u.username, 'test_user', 'Incorrect user returned.')

    def test_get_user_anonymous(self):
        req = MagicMock(spec=Request)
        req.user = AnonymousUser()
        u = _get_user(req)
        self.assertEqual(u, None, 'Anonymous user not handled correctly.')

    def test_get_file_id(self):
        fid = _get_file_id()
        self.assertTrue(isinstance(fid, text_type),
                        'The file ID must be a string.')
        id_format = re.compile('^([%s]){22}$' % (shortuuid.get_alphabet()))
        self.assertRegex(fid, id_format, ('The generated ID does not match '
                                          'the defined ID format.'))

    def test_get_base_dir_with_str(self):
        test_dir_name = '/tmp/testdir'
        old_base_dir = local_settings.BASE_DIR
        try:
            local_settings.BASE_DIR = test_dir_name
            bd = get_local_settings_base_dir()
            self.assertIsInstance(
                bd, str, 'The base directory is not a string.')
            self.assertEqual(
                bd, test_dir_name, 'The test directory name doesn\'t match.')
        finally:
            local_settings.BASE_DIR = old_base_dir

    def test_get_base_dir_with_path(self):
        try:
            from pathlib import Path
            test_dir_name = Path('/tmp/testdir')
        except ImportError:
            test_dir_name = '/tmp/testdir'

        old_base_dir = local_settings.BASE_DIR
        try:
            local_settings.BASE_DIR = test_dir_name
            bd = get_local_settings_base_dir()
            self.assertIsInstance(
                bd, str, 'The base directory is not a string.')
            self.assertEqual(
                bd, str(test_dir_name),
                'The test directory name doesn\'t match.')
        finally:
            local_settings.BASE_DIR = old_base_dir
