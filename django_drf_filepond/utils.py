# A module containing some utility functions used by the views and uploaders
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
