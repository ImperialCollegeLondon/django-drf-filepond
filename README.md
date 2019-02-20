# django-drf-filepond: A filepond server implementation for Django + Django REST Framework

[![PyPI version](https://img.shields.io/pypi/v/django-drf-filepond.svg)](https://pypi.python.org/pypi/django-drf-filepond/) [![Build Status](https://travis-ci.org/ImperialCollegeLondon/django-drf-filepond.svg?branch=master)](https://travis-ci.org/ImperialCollegeLondon/django-drf-filepond) [![Documentation Status](https://readthedocs.org/projects/django-drf-filepond/badge/?version=latest)](http://django-drf-filepond.readthedocs.io/?badge=latest)

**django-drf-filepond** is a Django app that provides a [filepond](https://github.com/pqina/filepond) server-side implementation for Django/Django REST Framework projects. The app can be easily added to your Django projects to provide a server-side API for the filepond file upload library.

Further documentation and a tutorial are available at [https://django-drf-filepond.readthedocs.io](https://django-drf-filepond.readthedocs.io).

#### Installation

The app can be installed from PyPi:

```
pip install django-drf-filepond
```

or add it to your list of dependencies in a [_requirements.txt_](https://pip.pypa.io/en/stable/user_guide/#requirements-files) file.

#### Configuration

There are three key configuration updates to make within your Django application to set up django-drf-filepond:

###### 1. Add the app to INSTALLED_APPS:

Add 'django-drf-filepond' to `INSTALLED_APPS` in your Django settings file (e.g. `settings.py`):

```python
...

INSTALLED_APPS = [
	...,
	'django_drf_filepond'
]

...
```

###### 2. Set the temporary file upload location:

Set the location where you want django-drf-filepond to store temporary file uploads by adding the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` configuration variable to your settings file, e.g.:

```python
import os
...
DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, 'filepond-temp-uploads')
...
```

###### 3. Include the app urls into your main url configuration

Add the URL mappings for django-drf-filepond to your URL configuration in `urls.py`:

```python
from django.conf.urls import url, include

urlpatterns = [
	...
	url(r'^fp/', include('django_drf_filepond.urls')),
]
```

On the client side, you need to set the endpoints of the `process`, `revert`, `fetch`, `load` and `restore` functions to match the endpoint used in your path statement above. For example if the first parameter to `url` is `fp/` then the endpoint for the process function will be `/fp/process/`.

###### (Optional) 4. Set the permanent file store location

If you wish to let django-drf-filepond manage the permanent storage of file uploads  _(note that this is required if you wish to use the `load` method)_, you need to set `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` in your application settings file, e.g.

```python
...
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.join(BASE_DIR, 'stored_uploads')
...
```
See _"Working with file uploads"_ below for more information on how to move temporary uploads to _django-drf-filepond_-managed permanent storage.

#### Working with file uploads

When a file is uploaded from a filepond client, the file is placed into a uniquely named directory within the temporary upload directory specified by the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` parameter. As per the filepond [server spec](https://pqina.nl/filepond/docs/patterns/api/server/), the server returns a unique identifier for the file upload. In this case, the identifier is a 22-character unique ID generated using the [shortuuid](https://github.com/skorokithakis/shortuuid) library. This ID is the name used for the directory created under `DJANGO_DRF_FILEPOND_UPLOAD_TMP` into which the file is placed. At present, the file also has a separate unique identifier which hides the original name of the file on the server filesystem. The original filename is stored within the django-drf-filepond app's database.

When/if the client subsequently submits the form associated with the filepond instance that triggered the upload, the unique directory ID will be passed and this can be used to look up the temporary file.

There are two different approaches for handling files that need to be stored permanently on a server after being uploaded from a filepond client via django-drf-filepond. _These two approaches are not mutually exclusive and you can choose to use one approach for some files and the other approach for other files if you wish._

###### 1. Manual handling of file storage

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

###### 2. Use django-drf-filepond's API to store a temporary upload to permanent storage

**Note:** You must use this approach for storing any files that you subsequently want to access using filepond's `load` function.

Using this approach, the file is stored to a location under the _django-drf-filepond_ file storage directory as set by the `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` setting.

```python
from django_drf_filepond.api import store_upload

# Given a variable upload_id containing a 22-character unique file upload ID:
su = store_upload(upload_id, destination_file_path='target_dir/filename.ext')
# destination_file_path is a relative path (including target filename. 
# The path will created under the file store directory and the original 
# temporary upload will be deleted.

```

The `destination_file_path` parameter passed to `store_upload` should be relative to the base upload location as defined by `DJANGO_DRF_FILEPOND_FILE_STORE_PATH`. If you pass a path that begins with `/`, the leading `/` will be removed and the path will be interpreted as being relative to `DJANGO_DRF_FILEPOND_FILE_STORE_PATH`. The path that you provide should include the filename that you would like the file stored as. 

### License

This repository is licensed under a BSD 3-Clause license. Please see the [LICENSE](LICENSE) file in the root of the repository.

### Acknowledgements

Thanks to [pqina](https://github.com/pqina) for producing the [filepond](https://pqina.nl/filepond/) file upload library that this Django app provides server-side support for.

The django-drf-filepond app has been built as part of work that is being supported by UK Research and Innovation (Engineering and Phsycial Sciences Research Council) under grant EP/R025460/1.
