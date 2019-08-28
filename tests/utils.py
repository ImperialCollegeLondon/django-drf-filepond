# Some util functions for django-drf-filepond tests
import logging
import os

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
