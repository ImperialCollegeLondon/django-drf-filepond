Installation
============

The app can be installed from PyPi::

	pip install django-drf-filepond

or add it to your list of dependencies in a *requirements.txt* file.

Configuration
-------------

There are three key configuration updates to make within your Django 
application to set up django-drf-filepond:

1. Add the app to INSTALLED_APPS:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add 'django-drf-filepond' to ``INSTALLED_APPS`` in your Django settings 
file (e.g. ``settings.py``)::

	...
	
	INSTALLED_APPS = [
		...,
		'django_drf_filepond'
	]
	
	...

You will need to re-run ``python manage.py migrate`` to update the database 
with the table(s) used by django-drf-filepond.

2. Set the temporary file upload location:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set the location where you want django-drf-filepond to store temporary 
file uploads by adding the ``DJANGO_DRF_FILEPOND_UPLOAD_TMP`` configuration 
variable to your settings file, e.g.::

	import os
	...
	DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, 'filepond-temp-uploads')
	...

3. Include the app urls into your main url configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add the URL mappings for django-drf-filepond to your URL configuration 
in ``urls.py``::

	from django.conf.urls import url, include
	
	urlpatterns = [
		...
		url(r'^fp/', include('django_drf_filepond.urls')),
	]

On the client side, you need to set the endpoints of the ``process``, 
``revert``, ``fetch``, ``load`` and ``restore`` functions to match the 
endpoint used in your path statement above. For example if the first 
parameter to ``url`` is ``^fp/`` then the endpoint for the ``process`` 
function will be ``/fp/process/``.

Logging
-------

django-drf-filepond outputs a variety of debug logging messages. You can 
configure logging for the app through Django's `logging configuration <https://docs.djangoproject.com/en/2.1/topics/logging/>`_ in your 
Django `application settings <https://docs.djangoproject.com/en/2.1/topics/settings/>`_.

For example, taking a basic logging configuration such as the first example 
configuration in Django's `logging documentation examples <https://docs.djangoproject.com/en/2.1/topics/logging/#examples>`_, adding 
the following to the ``loggers`` section of the ``LOGGING`` configuration dictionary will 
enable DEBUG output for all modules in the ``django_drf_filepond`` package::

    'django_drf_filepond': {
        'handlers': ['file'],
        'level': 'DEBUG',
    },
    
You can also enable logging for individual modules or set different logging 
levels for different modules by specifying the fully qualified module name in 
the configuration, for example::

    'django_drf_filepond.views': {
        'handlers': ['file'],
        'level': 'DEBUG',
        'propagate': False,
    },
    'django_drf_filepond.models': {
        'handlers': ['file'],
        'level': 'INFO',
        'propagate': False,
    },
 