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

1. Use django-drf-filepond's API to store a temporary upload to permanent storage *(recommended)*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: You must use this approach for storing any files that you 
	subsequently want to access using filepond's ``load`` function.

Using this approach, the file is stored either to local storage or to a
remote storage service depending on the file store configuration you are
using.

1.1 ``store_upload``
#####################

``store_upload`` stores a temporary upload, uploaded as a result of adding
it to the filepond component in a web page, to permanent storage. 

If you have configured *django-drf-filepond* to use local file storage by
setting the ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` parameter in your
application settings, the file will be stored to a location under this
directory.

If you have configured a remote file store via *django-storages*, the stored
upload will be sent to the configured storage backend via *django-storages*.

**Parameters:**

``upload_id``: The unique ID assigned to the upload by *django-drf-filepond*
when the file was initially uploaded via filepond.

``destination_file_path``: The location where the file should be stored.
This location will be appended to the base file storage location as defined
using the `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` parameter, or, for remote
storage backends, the location configured using the relevant
*django-storages* parameters. If you pass an absolute path beginning with
``/``, the leading ``/`` will be removed. The path that you provide should
also include the target filename.

**Returns:**

A ``django_drf_filepond.models.StoredUpload`` object representing the
stored upload.

Raises ``django.core.exceptions.ImproperlyConfigured`` if using a local
file store and `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` has not been set.

**Raises** ``ValueError`` **if:**

 - an ``upload_id`` is provided in an invalid format
 - the ``destination_file_path`` is not provided
 - a ``django_drf_filepond.models.TemporaryUpload`` record for the provided
   ``upload_id`` is not found

**Example:**

.. code:: python

	from django_drf_filepond.api import store_upload
	
	# Given a variable upload_id containing a 22-character unique file upload ID:
	su = store_upload(upload_id, destination_file_path='target_dir/filename.ext')
	# destination_file_path is a relative path (including target filename. 
	# The path will created under the file store directory and the original 
	# temporary upload will be deleted.

1.2 ``get_stored_upload`` / ``get_stored_upload_file_data``
############################################################

Get access to a stored upload and the associated file data.

``get_stored_upload``: Given an ``upload_id``, return the associated 
``django_drf_filepond.models.StoredUpload`` object.

Throws ``django_drf_filepond.models.StoredUpload.DoesNotExist`` if a
database record doesn't exist for the specified ``upload_id``.

``get_stored_upload_file_data``: Given a StoredUpload object, return the
file data for the upload as a Python
`file-like object <https://docs.python.org/3/glossary.html#term-file-like-object>`_.

**Parameters:**

``stored_upload``: A ``django_drf_filepond.models.StoredUpload`` object for
which you want retrieve the file data.

**Returns:**

Returns a tuple ``(filename, bytes_io)`` where ``filename`` is a string
representing the name of the stored file being returned and ``bytes_io``
is an ``io.BytesIO`` object from which the file data can be read. If an
error occurs, raises an exception:

 - ``django_drf_filepond.exceptions.ConfigurationError``: Thrown if using a local file store and ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` is not set or the specified location does not exist, or is not a directory. 
 
 - ``FileNotFoundError``: Thrown if using a remote file store and the file store API reports that the file doesn't exist. If using a local file store, thrown if the file does not exist or the location is a directory and not a file.
 
 - ``IOError``: Thrown if using a local file store and reading the file fails.

**Example:**

.. code:: python

	from django_drf_filepond.api import get_stored_upload
	from django_drf_filepond.api import get_stored_upload_file_data
	
	# Given a variable upload_id containing a 22-character unique 
	# upload ID representing a stored upload:
	su = get_store_upload(upload_id)
	(filename, bytes_io) = get_store_upload_file_data(su)
	file_data = bytes_io.read()
	
1.3 ``delete_stored_upload``
#############################

``delete_stored_upload`` deletes a stored upload record and, optionally,
the associated file that is stored on either a local disk or a remote file
storage service.

**Parameters:**

``upload_id``: The unique ID assigned to the upload by *django-drf-filepond*
when the file was initially uploaded via filepond.

``delete_file``: ``True`` to delete the file associated with the record,
``False`` to leave the file in place.

**Returns:**

Returns ``True`` if the stored upload is deleted successfully, otherwise
raises an exception:

 - ``django_drf_filepond.models.StoredUpload.DoesNotExist`` exception if no upload exists for the specified ``upload_id``.
 - ``django_drf_filepond.exceptions.ConfigurationError``: Thrown if using a local file store and ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` is not set or the specified location does not exist, or is not a directory.
 - ``FileNotFoundError``: Thrown if using a remote file store and the file store API reports that the file doesn't exist. If using a local file store, thrown if the file does not exist or the location is a directory and not a file.
 - ``OSError``: Thrown if using a local file store and the file deletion fails.

**Example:**

.. code:: python

	from django_drf_filepond.api import delete_stored_upload
	
	# Given a variable upload_id containing a 22-character unique 
	# upload ID representing a stored upload:
	delete_stored_upload(upload_id, delete_file=True)
	# delete_file=True will delete the file from the local 
	# disk or the remote storage service. 
 
2. Manual handling of file storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using this approach, you move the file initially stored as a temporary 
upload by *django-drf-filepond* to a storage location of your choice and 
the file then becomes independent of *django-drf-filepond*. The following 
example shows how to lookup a temporary upload given its unique upload ID 
and move it to a permanent storage location. The temporary upload record 
is then deleted and *django-drf-filepond* no longer has any awareness of 
the file:

.. code:: python

	import os
	from django_drf_filepond.models import TemporaryUpload
	
	# Get the temporary upload record
	tu = TemporaryUpload.objects.get(upload_id='<22-char unique ID>')
	
	# Move the file somewhere for permanent storage
	# The file will be saved with its original name
	os.rename(tu.get_file_path(), '/path/to/permanent/location/%s' % tu.upload_name)
	
	# Delete the temporary upload record and the temporary directory
	tu.delete()