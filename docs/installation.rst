Installation
============

The app can be installed from PyPi::

	pip install django-drf-filepond

or add it to your list of dependencies in a *requirements.txt* file.

Configuration
-------------

There are three required configuration updates to make within your Django 
application to set up django-drf-filepond. A number of additional 
configuration options may be specified if you're using optional features:

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

.. note:: It is strongly recommended that you set 
	``DJANGO_DRF_FILEPOND_UPLOAD_TMP``. If you do not set this variable, the 
	app will set a default location for the storage of temporary uploads. 
	This is ``BASE_DIR/filepond_uploads`` where ``BASE_DIR`` is the variable 
	defined by default in an auto-generated Django settings file pointing to 
	the top-level directory of your Django project. If your settings do not 
	contain ``BASE_DIR`` the app will default to storing the 
	``filepond_uploads`` directory in the ``django-drf-filepond`` app  
	directory, wherever that is located. Note that this may be within the  
	``lib`` directory of a virtualenv.

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

(Optional) 4. File storage configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Initially, uploaded files are stored in a temporary staging area (the 
location you set in item 2 above, with the ``DJANGO_DRF_FILEPOND_UPLOAD_TMP`` 
parameter. At this point, an uploaded file is still shown in the filepond UI  
on the client and the user can choose to cancel the upload resulting in the  
file being deleted from temporary storage and the upload being cancelled.

Once the user confirms the file upload(s), e.g. by submitting the form in 
which the filepond component is embedded, any temporary uploads need to be  
moved to permanent storage. You can handle this yourself by interacting 
directly with django-drf-filepond's ``TemporaryUpload`` model to find and   
store the uploaded files, or you can use django-drf-filepond's API to store  
files and have the library assist you in managing them. Using this approach,  
you can also make use of filepond's ``load`` method, this is not possible if 
you manage file storage independently of django-drf-filepond.  

There are two different options for file storage:

- Use a location on a local filesystem on the host server for permanent file storage
   
- Use a remote file storage backend via the `django-storages <https://django-storages.readthedocs.io/en/latest>`_ library 

Section 4.1 details configuration for using the local filesystem for 
storage of filepond uploads.

Section 4.2 details configuration for using the django-storages library to 
enable remote storage of filepond uploads.

If you wish to let django-drf-filepond manage the permanent storage of file 
uploads (note that this is required if you wish to use the load method), 
you need to set ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` in your application 
settings file, e.g.::

	...
	DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.join(BASE_DIR, 'stored_uploads')
	...

(Optional) 4.1 Storage of filepond uploads using the local file system
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Information on storage of file uploads using the local filesystem

(Optional) 4.2 Remote storage of filepond uploads via django-storages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Information on storage of file uploads using django-storages

Advanced Configuration Options
------------------------------

There are some optional additional configuration parameters that can be used 
to manage other features of the library. These are detailed in this section.

``DJANGO_DRF_FILEPOND_DELETE_UPLOAD_TMP_DIRS`` (*default*: ``True``):

	When a file is uploaded from a client using *filepond*, or pulled from a 
	remote URL as a result of a call to the fetch endpoint from the filepond 
	client, a temporary directory is created for the uploaded/fetched file  
	to be placed into as a temporary upload. When the temporary upload is 
	subsequently removed, either because it is cancelled or because it is 
	moved to permanent storage, the file stored as a temporary upload is 
	removed along with the temporary directory that it is stored in. The 
	approach of creating a temporary directory named with a unique ID 
	specific to the individual file being uploaded is as described in the 
	`filepond server documentation <https://pqina.nl/filepond/docs/patterns/api/server/#process>`_.
	
	In cases where there are large numbers of temporary uploads being 
	created and removed, if there is a need to reduce the load on the 
	filesystem, setting ``DJANGO_DRF_FILEPOND_DELETE_UPLOAD_TMP_DIRS`` to 
	``False`` will prevent the temporary directories from being removed when 
	a temporary upload is deleted. The files within those directories will 
	still be removed.
	
	*NOTE:* If you set ``DJANGO_DRF_FILEPOND_DELETE_UPLOAD_TMP_DIRS`` to   
	``False``, you will need to have some alternative periodic "garbage   
	collection" process in operation to remove all empty temporary   
	directories in order to avoid a build up of potentially very large   
	numbers of empty directories on the filesystem.
	   
Using a non-standard element name for your client-side filepond instance:

	If you have a filepond instance on your client web page that uses an  
	element name other than the default ``filepond``, *django-drf-filepond* 
	can now handle this. For example, if you have multiple filepond 
	instances on a page, you will need to give each instance a different 
	name. To take advatage of this feature, you will need to inject an   
	additional parameter ``fp_upload_field`` into the HTTP upload request 
	which provides the name of the filepond form instance to process. An 
	example of this is shown in the `issue <https://github.com/ImperialCollegeLondon/django-drf-filepond/issues/4#issue-412361507>`_ 
	describing the request for this feature.   
	

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
 