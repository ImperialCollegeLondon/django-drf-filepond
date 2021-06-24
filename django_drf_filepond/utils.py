# A module containing some utility functions used by the views and uploaders
import django_drf_filepond.drf_filepond_settings as local_settings
from django.contrib.auth.models import AnonymousUser
import shortuuid
import six


# Get the user associated with the provided request. If we have an anonymous
# user object then return None
def _get_user(request):
    upload_user = getattr(request, 'user', None)
    if isinstance(upload_user, AnonymousUser):
        upload_user = None
    return upload_user


# Generate a file or upload ID. At present, this is used for generating both
# ID types since they both have the same specification.
def _get_file_id():
    file_id = shortuuid.uuid()
    return six.ensure_text(file_id)


# Get the BASE_DIR variable from local_settings and process it to ensure that
# it can be used in django_drf_filepond across Python 2.7, 3.5 and 3.6+.
# Need to take into account that this may be a regular string or a
# pathlib.Path object. django-drf-filepond expects to work with BASE_DIR as a
# string so return a string regardless of the type of BASE_DIR. To maintain
# suport for Python 2.7, need to handle the case where pathlib.Path doesn't
# exist...
def get_local_settings_base_dir():
    base_dir = local_settings.BASE_DIR
    return _process_base_dir(base_dir)


# Process the provided BASE_DIR variable
def _process_base_dir(base_dir):
    try:
        from pathlib import Path
    except ImportError:
        return base_dir

    if isinstance(base_dir, Path):
        return str(base_dir)
    return base_dir
