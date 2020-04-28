import logging
import re

from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase
from rest_framework.request import Request
import shortuuid
from six import text_type

from django_drf_filepond.utils import _get_user, _get_file_id


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
