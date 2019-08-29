Using the library
=================

.. _Working with file uploads:

Working with file uploads
-------------------------

When a file is uploaded from a filepond client, the file is placed into a 
uniquely named directory within the temporary upload directory specified by 
the ``DJANGO_DRF_FILEPOND_UPLOAD_TMP`` parameter. As per the filepond 
`server spec <https://pqina.nl/filepond/docs/patterns/api/server/>`_, the 
server returns a unique identifier for the file upload. In this case, 
the identifier is a 22-character unique ID generated using the 
`shortuuid <https://github.com/skorokithakis/shortuuid>`_ library. This 
ID is the name used for the directory created under 
``DJANGO_DRF_FILEPOND_UPLOAD_TMP`` into which the file is placed. At 
present, the file also has a separate unique identifier which hides the 
original name of the file on the server filesystem. The original filename 
is stored within the django-drf-filepond app's database. The use of a unique 
ID for the stored file name also allows multiple uploads with the same file 
name in a single upload session without causing problems with overwriting of 
files in the temporary upload directory.

When/if the client subsequently submits the form associated with the 
filepond instance that triggered the upload, the unique directory ID 
will be passed to the server by the client and this can be used to look up 
the temporary file. 

There are two different approaches for handling files that need to be stored 
permanently on a server after being uploaded from a filepond client via 
django-drf-filepond. *These two approaches are not mutually exclusive and 
you can choose to use one approach for some files and the other approach for 
other files if you wish.*

Your application can either handle file uploads manually, by interacting 
directly with django-drf-filepond's ``TemporaryUpload`` model to find and 
store the uploaded files, or it can use django-drf-filepond's API to store    
files. Using the latter approach, you can also make use of filepond's 
``load`` method which is not possible if you choose to manage file storage 
independently of django-drf-filepond.  

1. Use django-drf-filepond's API to store a temporary upload to permanent storage *(recommended)*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: You must use this approach for storing any files that you 
	subsequently want to access using filepond's ``load`` function.

Using this approach, the file is stored either to a location on the host 
server under the *django-drf-filepond* file storage directory as set by the 
``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` setting, or on a remote file storage 
system via django-storages if you have this configured.::

	from django_drf_filepond.api import store_upload
	
	# Given a variable upload_id containing a 22-character unique file upload ID:
	su = store_upload(upload_id, destination_file_path='target_dir/filename.ext')
	# destination_file_path is a relative path (including target filename. 
	# The path will created under the file store directory and the original 
	# temporary upload will be deleted.
	
The ``destination_file_path`` parameter passed to ``store_upload`` should 
be relative to the base upload location. 

If the file is being stored on the local server, this is defined by the 
``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` parameter in your *settings.py* 
file. If you pass a path that begins with ``/``, the leading ``/`` will be 
removed and the path will be interpreted as being relative to 
``DJANGO_DRF_FILEPOND_FILE_STORE_PATH``. The path that you provide should 
include the filename that you would like the file stored as.

If the file is being stored to a remote location via django-storages, the 
file will be placed at the location defined by ``destination_file_path``, 
relative to the base file store location. If you pass a path that begins 
with ``/``, the leading ``/`` will be removed and the path will become 
relative. For example, if you are using Amazon S3-based storage, then your 
file will be stored at the specified location within the bucket configured 
in your django-storages configuration provided in your app's ``settings.py``.

A call to ``store_upload`` returns an instance of 
``django_drf_filepond.models.StoredUpload``. A stored upload object is 
identified by a unique ``upload_id``. You can use this value to lookup the 
database record associated with a stored file at a later time. Via the 
``StoredUpload`` database record you can *read* the stored file or *delete* 
it. File deletion is subject to support within the django-storages backend 
that you're using.

2. Manual handling of file storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using this approach, you move the file initially stored as a temporary 
upload by *django-drf-filepond* to a storage location of your choice and 
the file then becomes independent of *django-drf-filepond*. The following 
example shows how to lookup a temporary upload given its unique upload ID 
and move it to a permanent storage location. The temporary upload record 
is then deleted and *django-drf-filepond* no longer has any awareness of 
the file::

	import os
	from django_drf_filepond.models import TemporaryUpload
	
	# Get the temporary upload record
	tu = TemporaryUpload.objects.get(upload_id='<22-char unique ID>')
	
	# Move the file somewhere for permanent storage
	# The file will be saved with its original name
	os.rename(tu.get_file_path(), '/path/to/permanent/location/%s' % tu.upload_name)
	
	# Delete the temporary upload record and the temporary directory
	tu.delete()