from io import BytesIO
import logging
import os
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import encode_multipart, RequestFactory
from django.urls import reverse

from django_drf_filepond import drf_filepond_settings
import django_drf_filepond.views as views
from tests.utils import remove_file_upload_dir_if_required

LOG = logging.getLogger(__name__)
#
# This test class tests the functionality of the ProcessView when it is used
# for handling chunked uploads.
#
# test_
#


class ProcessChunkedTestCase(TestCase):

    def setUp(self):
        pass

    def test_process_data(self):
        pass
