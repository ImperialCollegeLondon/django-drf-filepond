# django-drf-filepond: A filepond server implementation for Django + Django REST Framework

[![PyPI version](https://img.shields.io/pypi/v/django-drf-filepond.svg)](https://pypi.python.org/pypi/django-drf-filepond/) [![Supported python versions](https://img.shields.io/pypi/pyversions/django-drf-filepond)](https://pypi.python.org/pypi/django-drf-filepond/) [![test status](https://github.com/ImperialCollegeLondon/django-drf-filepond/actions/workflows/python-test.yml/badge.svg)](https://github.com/ImperialCollegeLondon/django-drf-filepond/actions/workflows/python-test.yml) [![Documentation Status](https://readthedocs.org/projects/django-drf-filepond/badge/?version=latest)](http://django-drf-filepond.readthedocs.io/?badge=latest)

**django-drf-filepond** is a Django app that provides a [filepond](https://github.com/pqina/filepond) server-side implementation for Django/Django REST Framework projects. The app can be easily added to your Django projects to provide a server-side API for the filepond file upload library.

django-drf-filepond supports remote storage of uploads via [*django-storages*](https://django-storages.readthedocs.io/)

:new: Support for large file uploads (> ~2GB) now available from version 0.4.0 (see [#57](https://github.com/ImperialCollegeLondon/django-drf-filepond/issues/57)).<br/>
:new: Support for filepond chunked uploads now available from version 0.3.0.


:warning: **Release v0.4.0 includes a database update** in relation to the large upload support. If you don't wish to apply DB migrations within your application at this stage, please continue to use django-drf-filepond [v0.3.1](https://pypi.org/project/django-drf-filepond/0.3.1/). :warning:


Further documentation and a tutorial are available at [https://django-drf-filepond.readthedocs.io](https://django-drf-filepond.readthedocs.io).

### Installation

The app can be installed from PyPi:

```
pip install django-drf-filepond
```

or add it to your list of dependencies in a [_requirements.txt_](https://pip.pypa.io/en/stable/user_guide/#requirements-files) file.

### Configuration

There are three key configuration updates to make within your Django application to set up django-drf-filepond:

##### 1. Add the app to INSTALLED_APPS:

Add 'django-drf-filepond' to `INSTALLED_APPS` in your Django settings file (e.g. `settings.py`):

```python
...

INSTALLED_APPS = [
	...,
	'django_drf_filepond'
]

...
```

##### 2. Set the temporary file upload location:

Set the location where you want django-drf-filepond to store temporary file uploads by adding the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` configuration variable to your settings file, e.g.:

```python
import os
...
DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, 'filepond-temp-uploads')
...
```

##### 3. Include the app urls into your main url configuration

Add the URL mappings for django-drf-filepond to your URL configuration in `urls.py`:

```python
from django.urls import re_path, include

urlpatterns = [
	...
	re_path(r'^fp/', include('django_drf_filepond.urls')),
]
```

On the client side, you need to set the endpoints of the `process`, `revert`, `fetch`, `load`, `restore` and `patch` functions to match the endpoint used in your path statement above. For example if the first parameter to `re_path` is `fp/` then the endpoint for the process function will be `/fp/process/`.

##### (Optional) 4. File storage configuration

Initially, uploaded files are stored in a temporary staging area (the location you set in item 2 above, with the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` parameter. At this point, an uploaded file is still shown in the filepond UI on the client and the user can choose to cancel the upload resulting in the file being deleted from temporary storage and the upload being cancelled. When a user confirms a file upload, e.g. by submitting the form in which the filepond component is embedded, any temporary uploads need to be moved to a permanent storage location.

There are three different options for file storage:

- Use a location on a local filesystem on the host server for file storage 
  (see Section 4.1)
   
- Use a remote file storage backend via the [*django-storages*](https://django-storages.readthedocs.io/en/latest>) library (see Section 4.2)

- Manage file storage yourself, independently of *django-drf-filepond* (in this case, filepond ``load`` functionality is not supported)

More detailed information on handling file uploads and using the *django-drf-filepond* API to store them is provided in the *Working with file uploads* section below.

###### 4.1 Storage of filepond uploads using the local file system

To use the local filesystem for storage, you need to specify where to store files. Set the `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` parameter in your Django application settings file to specify the base location where stored uploads will be placed, e.g.:

```python
...
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.join(BASE_DIR, 'stored_uploads')
...
```

The specified path for each stored upload will then be created relative to this location. For example, given the setting shown above, if `BASE_DIR` were `/tmp/django-drf-filepond`, then a temporary upload with the specified target location of either `/mystoredupload/uploaded_file.txt` or `mystoredupload/uploaded_file.txt` would be stored to `/tmp/django-drf-filepond/stored_uploads/mystoredupload/uploaded_file.txt`

When using local file storage, `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` is the only required setting.

###### 4.2 Remote storage of filepond uploads via django-storages

The [*django-storages*](https://github.com/jschneier/django-storages>) library provides support for a number of different remote file storage backends. The [django-storages documentation](https://django-storages.readthedocs.io/en/latest) lists the supported backends.

To enable *django-storages* support for django-drf-filepond, set the `DJANGO_DRF_FILEPOND_STORAGES_BACKEND` parameter in your application configuration to the *django-storages* backend that you wish to use. You need to specify the fully-qualified class name for the storage backend that you want to use. This is the same value that would be used for the *django-storages* `DEFAULT_FILE_STORAGE` parameter and the required value can be found either by looking at the [django-storages documentation](https://django-storages.readthedocs.io/en/latest) for the backend that you want to use, or by looking at the [code on GitHub](https://github.com/jschneier/django-storages/tree/master/storages/backends).

For example, if you want to use the SFTP storage backend, add the following to your application settings:

```python
...
DJANGO_DRF_FILEPOND_STORAGES_BACKEND = \
	'storages.backends.sftpstorage.SFTPStorage'
...
```

or, for the Amazon S3 backend:

```python
...
DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
...
```

For each storage backend, there are a number of additional *django-storages* configuration options that must be specified. These are detailed in the *django-storages* documentation.

The following is an example of a complete set of configuration parameters for using an Amazon S3 storage backend for django-drf-filepond via django-storages:

```python
	...
	DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
	AWS_ACCESS_KEY_ID = '<YOUR AWS ACCESS KEY>'
	AWS_SECRET_ACCESS_KEY = '<YOUR AWS SECRET KEY>'
	AWS_STORAGE_BUCKET_NAME = 'django-drf-filepond'
	AWS_AUTO_CREATE_BUCKET = True
	AWS_S3_REGION_NAME = 'eu-west-1'
	...
```

*NOTE: django-storages is now included as a core dependency of django-drf-filepond. However, the different django-storages backends each have their own additional dependencies __which you need to install manually__ or add to your own app's dependencies.*
	
*You can add additional dependencies using* `pip` *by specifying the optional extras feature tag, e.g. to install additional dependencies required for django-storages' Amazon S3 support run*:

```shell
	$ pip install django-storages[boto3]
```	

See the *Working with file uploads* section for more details on how to use the django-drf-filepond API to store files to a local or remote file store. 

*NOTE:* `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` *is not used when using a remote file store backend. It is recommended to remove this setting or leave it set to None.*
	
*The base storage location for a remote file storage backend from django-storages is set using a setting specific to the backend that you are using - see the django-storages documentation for your chosen backend for further information.*

###### (Optional) 4. Set the permanent file store location

If you wish to let django-drf-filepond manage the permanent storage of file uploads  _(note that this is required if you wish to use the `load` method)_, you need to set `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` in your application settings file, e.g.

```python
...
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.join(BASE_DIR, 'stored_uploads')
...
```
See _"Working with file uploads"_ below for more information on how to move temporary uploads to _django-drf-filepond_-managed permanent storage.

### Working with file uploads

When a file is uploaded from a filepond client, the file is placed into a uniquely named directory within the temporary upload directory specified by the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` parameter. As per the filepond [server spec](https://pqina.nl/filepond/docs/patterns/api/server/), the server returns a unique identifier for the file upload. In this case, the identifier is a 22-character unique ID generated using the [shortuuid](https://github.com/skorokithakis/shortuuid) library. This ID is the name used for the directory created under `DJANGO_DRF_FILEPOND_UPLOAD_TMP` into which the file is placed. At present, the file also has a separate unique identifier which hides the original name of the file on the server filesystem. The original filename is stored within the django-drf-filepond app's database.

When/if the client subsequently submits the form associated with the filepond instance that triggered the upload, the unique directory ID will be passed and this can be used to look up the temporary file.

#### Chunked uploads

_django-drf-filepond_ now supports filepond [chunked uploads](https://pqina.nl/filepond/docs/patterns/api/server/#chunk-uploads). There is no configuration required for _django-drf-filepond_ on the server side to handle chunked uploads.

On the client side, you need to ensure that your [filepond configuration](https://pqina.nl/filepond/docs/patterns/api/filepond-instance/#server-configuration) specifies server endpoints for both the `process` and `patch` methods and that you have the required configuration options in place to enable chunked uploads. For example, if you want to enable `chunkUploads` and send uploads in 500,000 byte chunks, your filepond configuration should include properties similar to the following:

```python
FilePond.setOptions({
    ...
    chunkUploads: true,
    chunkSize: 500000,
    server: {
        url: 'https://.../fp',
        process: '/process/',
        patch: '/patch/',
        revert: '/revert/',
        fetch: '/fetch/?target='
    }
    ...
});
```

#### Storing file uploads

There are two different approaches for handling temporary uploads that need to be stored permanently on a server after being uploaded from a filepond client via django-drf-filepond. _These two approaches are not mutually exclusive and you can choose to use one approach for some files and the other approach for other files if you wish._



##### 1. Manual handling of file storage

Using this approach, you move the file initially stored as a temporary upload by _django-drf-filepond_ to a storage location of your choice and the file then becomes independent of _django-drf-filepond_. The following example shows how to lookup a temporary upload given its unique upload ID and move it to a permanent storage location. The temporary upload record is then deleted and _django-drf-filepond_ no longer has any awareness of the file:

```python
import os
from django_drf_filepond.models import TemporaryUpload

# Get the temporary upload record
tu = TemporaryUpload.objects.get(upload_id='<22-char unique ID>')

# Move the file somewhere for permanent storage
# The file will be saved with its original name
os.rename(tu.get_file_path(), '/path/to/permanent/location/%s' % tu.upload_name)

# Delete the temporary upload record and the temporary directory
tu.delete()
```

##### 2. Use django-drf-filepond's API to store a temporary upload to permanent storage

**Note:** You must use this approach for storing any files that you subsequently want to access using filepond's `load` function.

Using this approach, the file is stored either to local storage or to a remote storage service depending on the file store configuration you are using. 

###### 2.1 `store_upload`

`store_upload` stores a temporary upload, uploaded as a result of adding it to the filepond component in a web page, to permanent storage. 

If you have configured *django-drf-filepond* to use local file storage by setting the `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` parameter in your application settings, the file will be stored to a location under this directory.

If you have configured a remote file store via *django-storages*, the stored upload will be sent to the configured storage backend via *django-storages*.

_**Parameters:**_

`upload_id`: The unique ID assigned to the upload by *django-drf-filepond* when the file was initially uploaded via filepond.

`destination_file_path`: The location where the file should be stored. This location will be appended to the base file storage location as defined using the `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` parameter, or, for remote storage backends, the location configured using the relevant *django-storages* parameters. If you pass an absolute path beginning with `/`, the leading `/` will be removed. The path that you provide should also include the target filename.

_**Returns:**_

A `django_drf_filepond.models.StoredUpload` object representing the stored upload.

Raises `django.core.exceptions.ImproperlyConfigured` if using a local file store and `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` has not been set.

Raises `ValueError` if:

 - an `upload_id` is provided in an invalid format
 - the `destination_file_path` is not provided
 - a `django_drf_filepond.models.TemporaryUpload` record for the provided `upload_id` is not found





*Example:*

```python
from django_drf_filepond.api import store_upload

# Given a variable upload_id containing a 22-character unique file upload ID:
su = store_upload(upload_id, destination_file_path='target_dir/filename.ext')
# destination_file_path is a relative path (including target filename. 
# The path will created under the file store directory and the original 
# temporary upload will be deleted.

``` 

###### 2.2 `get_stored_upload` / `get_stored_upload_file_data`

Get access to a stored upload and the associated file data.

`get_stored_upload`: Given an `upload_id`, return the associated `django_drf_filepond.models.StoredUpload` object.

Throws `django_drf_filepond.models.StoredUpload.DoesNotExist` if a database record doesn't exist for the specified `upload_id`.

`get_stored_upload_file_data`: Given a StoredUpload object, return the file data for the upload as a Python [file-like object](https://docs.python.org/3/glossary.html#term-file-like-object).

_**Parameters:**_

`stored_upload`: A `django_drf_filepond.models.StoredUpload` object for which you want retrieve the file data.

_**Returns:**_

Returns a tuple `(filename, bytes_io)` where `filename` is a string representing the name of the stored file being returned and `bytes_io` is an `io.BytesIO` object from which the file data can be read. If an error occurs, raises an exception:

 - `django_drf_filepond.exceptions.ConfigurationError`: Thrown if using a local file store and `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` is not set or the specified location does not exist, or is not a directory.
 - `FileNotFoundError`: Thrown if using a remote file store and the file store API reports that the file doesn't exist. If using a local file store, thrown if the file does not exist or the location is a directory and not a file.
 - `IOError`: Thrown if using a local file store and reading the file fails.

*Example:*

```python
from django_drf_filepond.api import get_stored_upload
from django_drf_filepond.api import get_stored_upload_file_data

# Given a variable upload_id containing a 22-character unique 
# upload ID representing a stored upload:
su = get_stored_upload(upload_id)
(filename, bytes_io) = get_stored_upload_file_data(su)
file_data = bytes_io.read()
``` 

###### 2.3 `delete_stored_upload`

`delete_stored_upload` deletes a stored upload record and, optionally, the associated file that is stored on either a local disk or a remote file storage service.

_**Parameters:**_

`upload_id`: The unique ID assigned to the upload by *django-drf-filepond* when the file was initially uploaded via filepond.

`delete_file`: `True` to delete the file associated with the record, `False` to leave the file in place.

_**Returns:**_

Returns `True` if the stored upload is deleted successfully, otherwise raises an exception:

 - `django_drf_filepond.models.StoredUpload.DoesNotExist` exception if no upload exists for the specified `upload_id`.
 - `django_drf_filepond.exceptions.ConfigurationError`: Thrown if using a local file store and `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` is not set or the specified location does not exist, or is not a directory.
 - `FileNotFoundError`: Thrown if using a remote file store and the file store API reports that the file doesn't exist. If using a local file store, thrown if the file does not exist or the location is a directory and not a file.
 - `OSError`: Thrown if using a local file store and the file deletion fails.

```python
from django_drf_filepond.api import delete_stored_upload

# Given a variable upload_id containing a 22-character unique 
# upload ID representing a stored upload:
delete_stored_upload(upload_id, delete_file=True)
# delete_file=True will delete the file from the local 
# disk or the remote storage service.
``` 

#### DRF Permissions

By default no permissions are applied on API endpoints. If you want to assign certain permissions such as ```rest_framework.permissions.IsAuthenticated``` you can do it like so:

```python
DJANGO_DRF_FILEPOND_PERMISSION_CLASSES = {
    'GET_FETCH': ['rest_framework.permissions.IsAuthenticated', ],
    'GET_LOAD': ['rest_framework.permissions.IsAuthenticated', ],
    'POST_PROCESS': ['rest_framework.permissions.IsAuthenticated', ],
    'GET_RESTORE': ['rest_framework.permissions.IsAuthenticated', ],
    'DELETE_REVERT': ['rest_framework.permissions.IsAuthenticated', ],
    'PATCH_PATCH': ['rest_framework.permissions.IsAuthenticated', ],
}
```

You can add more than one permission for each endpoint. 

The above list includes all the permission names currently defined on django-drf-filepond views. The naming convention used is `<METHOD_NAME>_<ENDPOINT_NAME>` where `<METHOD_NAME>` is the method name used for a request and `<ENDPOINT_NAME>` is the URL endpoint called. So, for example, a `POST` request to `/fp/process` would be handled by the permission classes defined for `POST_PROCESS`.

### License

This repository is licensed under a BSD 3-Clause license. Please see the [LICENSE](LICENSE) file in the root of the repository.

### Acknowledgements

Thanks to [pqina](https://github.com/pqina) for producing the [filepond](https://pqina.nl/filepond/) file upload library that this Django app provides server-side support for.

The django-drf-filepond app has been built as part of work that is being supported by UK Research and Innovation (Engineering and Physical Sciences Research Council) under grant EP/R025460/1.
