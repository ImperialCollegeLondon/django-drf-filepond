# Some util functions for django-drf-filepond tests
import logging
import os
from django.http.request import QueryDict

LOG = logging.getLogger(__name__)


def remove_file_upload_dir_if_required(dir_pre_exists, tmp_upload_dir):
    # If the directory for the temp file upload didn't exist at the
    # start of the test then it's just been created so remove it.
    if not dir_pre_exists:
        LOG.debug('Removing created upload dir <%s>' % tmp_upload_dir)
        try:
            os.rmdir(tmp_upload_dir)
        except OSError as e:
            LOG.error('Unable to remove the temp upload directory: %s'
                      % str(e))


# Sets up a query dict object including the provided test data for use in file
# upload test
def _setupRequestData(value_dict):
    if len(value_dict) == 0:
        return QueryDict()
    qd = QueryDict(mutable=True)
    for key in value_dict.keys():
        val = value_dict[key]
        if type(val) == list:
            for item in val:
                qd.update({key: item})
        else:
            qd.update({key: val})
    return qd
