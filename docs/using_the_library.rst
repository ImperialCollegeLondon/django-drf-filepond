Using the library
=================

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
is stored within the django-drf-filepond app's database.

When/if the client subsequently submits the form associated with the 
filepond instance that triggered the upload, the unique directory ID 
will be passed and this can be used to look up the temporary file::

	import os
	from django_drf_filepond.models import TemporaryUpload
	
	# Get the temporary upload record
	tu = TemporaryUpload.objects.get(upload_id='<22-char unique ID>')
	
	# Move the file somewhere for permanent storage
	# The file will be saved with its original name
	os.rename(tu.get_file_path(), '/path/to/permanent/location/%s' % tu.upload_name)
	
	# Delete the temporary upload record and the temporary directory
	tu.delete()
	
