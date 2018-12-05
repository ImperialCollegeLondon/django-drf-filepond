# django-drf-filepond: A filepond server implementation for Django + Django REST Framework

**django-drf-filepond** is a Django app that provides a [filepond](https://github.com/pqina/filepond) server-side implementation for Django/Django REST Framework projects. The app can be easily added to your Django projects to provide a server-side API for the filepond file upload library.

Further documentation and a tutorial are available at [https://django-drf-filepond.readthedocs.io](https://django-drf-filepond.readthedocs.io).

#### Installation

The app can be installed from PyPi:

```
pip install django-drf-filepond
```

or add it to your list of dependencies in a _requirements.txt_ file.

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

#### Working with file uploads

When a file is uploaded from a filepond client, the file is placed into a uniquely named directory within the temporary upload directory specified by the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` parameter. As per the filepond [server spec](https://pqina.nl/filepond/docs/patterns/api/server/), the server returns a unique identifier for the file upload. In this case, the identifier is a 22-character unique ID generated using the [shortuuid](https://github.com/skorokithakis/shortuuid) library. This ID is the name used for the directory created under `DJANGO_DRF_FILEPOND_UPLOAD_TMP` into which the file is placed. At present, the file also has a separate unique identifier which hides the original name of the file on the server filesystem. The original filename is stored within the django-drf-filepond app's database.

When/if the client subsequently submits the form associated with the filepond instance that triggered the upload, the unique directory ID will be passed and this can be used to look up the temporary file:

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