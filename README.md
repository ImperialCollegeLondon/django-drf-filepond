# django-drf-filepond: A filepond server implementation for Django + Django REST Framework

**django-drf-filepond** is a Django app that provides a [filepond](https://github.com/pqina/filepond) server-side implementation for Django/Django REST Framework projects. The app can be easily added to your Django projects to provide a server-side API for the filepond file upload library.

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

```
...

INSTALLED_APPS = [
	...,
	'django_drf_filepond'
]

...
```

###### 2. Set the temporary file upload location:

Set the location where you want django-drf-filepond to store temporary file uploads by adding the `DJANGO_DRF_FILEPOND_UPLOAD_TMP` configuration variable to your settings file, e.g.:

```
import os
...
DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, 'filepond-temp-uploads')
...
```

###### 3. Include the app urls into your main url configuration

Add the URL mappings for django-drf-filepond to your URL configuration in `urls.py`:

```
from django.conf.urls import url, include

urlpatterns = [
	...
	url(r'^fp/', include('django_drf_filepond.urls')),
]
```

On the client side, you need to set the endpoints of the `process`, `revert`, `fetch`, `load` and `restore` functions to match the endpoint used in your path statement above. For example if the first parameter to `url` is `fp/` then the endpoint for the process function will be `/fp/process/`.
