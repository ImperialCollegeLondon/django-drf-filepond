.. _Installation:

############
Installation
############

The app can be installed from PyPi::

	pip install django-drf-filepond

or add it to your list of dependencies in a *requirements.txt* file.

*************
Configuration
*************

There are three required configuration updates to make within your Django 
application to set up django-drf-filepond. A number of additional 
configuration options may be specified if you're using optional features:

1. Add the app to INSTALLED_APPS:
=================================

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
==========================================

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
	
.. note:: If you wish to set your file upload location to an directory
	outside of your Django application, i.e. something that is not below
	BASE_DIR, you should consider any security implications that may result
	from letting the app write to another location on disk and set the
	``DJANGO_DRF_FILEPOND_ALLOW_EXTERNAL_UPLOAD_DIR`` to ``True`` to confirm
	that you want to use a directory external to your application to store
	temporary uploads.


3. Include the app urls into your main url configuration
========================================================

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

An example client-side configuration might include configuration similar to the
following:: 

    FilePond.setOptions({
        ...
        server: {
            url: 'https://<your app domain>/fp',
            process: '/process/',
            patch: '/patch/',
            revert: '/revert/',
            fetch: '/fetch/?target=',
            load: '/load/?id=',
            restore: '/restore/?id='
        }
        ...
    });

Note that the `load` and `restore` endpoints in django-drf-filepond expect the
upload ID to be provided as an `id` query string parameter, hence the `?id=` at
the end of the query strings shown in the above example. For the `fetch`
endpoint, django-drf-filepond expects the target URL to be specified via a
query string parameter named `target`, again, as per the above sample
configuration.

See the `filepond server configuration <https://pqina.nl/filepond/docs/patterns/api/server/>`_
documentation for further examples.

(Optional) 4. File storage configuration
========================================

Initially, uploaded files are stored in a temporary staging area (the 
location you set in item 2 above, with the ``DJANGO_DRF_FILEPOND_UPLOAD_TMP`` 
parameter. At this point, an uploaded file is still shown in the filepond UI  
on the client and the user can choose to cancel the upload resulting in the  
file being deleted from temporary storage and the upload being cancelled. 
When a user confirms a file upload, e.g. by submitting the form in 
which the filepond component is embedded, any temporary uploads need to be  
moved to a permanent storage location.

There are three different options for file storage:

- Use a location on a local filesystem on the host server for file storage 
  (see Section 4.1_)
   
- **\*NEW\*** Use a remote file storage backend via the `django-storages <https://django-storages.readthedocs.io/en/latest>`_ 
  library (see Section 4.2_)

- Manage file storage yourself, independently of django-drf-filepond (in 
  this case, filepond ``load`` functionality is not supported)

More detailed information on handling file uploads and using the 
django-drf-filepond API to store them is provided 
in :ref:`Working with file uploads`.

.. _4.1:

4.1 Storage of filepond uploads using the local file system
----------------------------------------------------------------------

To use the local filesystem for storage, you need to specify where to store 
files. Set the ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` parameter in your  
Django application settings file to specify the base location where stored  
uploads will be placed, e.g.::

	...
	DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.join(BASE_DIR, 'stored_uploads')
	...

The specified path for each stored upload will then be created relative to 
this location. For example, given the setting shown above, if ``BASE_DIR`` 
were ``/tmp/django-drf-filepond``, then a temporary upload with the  
specified target location of either ``/mystoredupload/uploaded_file.txt`` or 
``mystoredupload/uploaded_file.txt`` would be stored to 
``/tmp/django-drf-filepond/stored_uploads/mystoredupload/uploaded_file.txt``

When using local file storage, ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` is the 
only required setting. 

.. _4.2:

4.2 Remote storage of filepond uploads via django-storages
---------------------------------------------------------------------

The `django-storages library <https://github.com/jschneier/django-storages>`_
provides support for a number of different remote file storage 
backends. The `django-storages documentation <https://django-storages.readthedocs.io/en/latest>`_ 
lists the supported backends. 

To enable django-storages support for django-drf-filepond, set the 
``DJANGO_DRF_FILEPOND_STORAGES_BACKEND`` parameter in your application 
configuration to the django-storages backend that you wish to use. You need 
to specify the fully-qualified class name for the storage backend that you 
want to use. This is the same value that would be used for the 
django-storages ``DEFAULT_FILE_STORAGE`` parameter and the required value 
can be found either by looking at the 
`django-storages documentation <https://django-storages.readthedocs.io/en/latest>`_ 
for the backend that you want to use, or by looking at the `code <https://github.com/jschneier/django-storages/tree/master/storages/backends>`_ 
in GitHub.

For example, if you want to use the SFTP storage backend, add the following 
to your application settings::

	...
	DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.sftpstorage.SFTPStorage'
	...
	
or, for the Amazon S3 backend::

	...
	DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
	...

For the Azure Storage backend, set::

	...
	DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.azure_storage.AzureStorage'
	...

For the Google Cloud Storage backend, set::

	...
	DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.gcloud.GoogleCloudStorage'
	...

*django-storages* provides support for several other storage backends including
`Digital Ocean <https://django-storages.readthedocs.io/en/latest/backends/digital-ocean-spaces.html>`_
and `Dropbox <https://django-storages.readthedocs.io/en/latest/backends/dropbox.html>`_.

For each storage backend, there are a number of additional *django-storages* 
configuration options that must be specified. These are detailed in the 
*django-storages* documentation. The specific set of parameters that you
need to provide depends on your chosen storage backend configuration. 

As an example, if you are using the Amazon S3 storage backend
and want to store uploads into a bucket named *filepond-uploads* in the
*eu-west-1* region, with the bucket and files set to be accessible only by
the user specified using the access/secret key, you would provide the
following set of parameters in your application's ``settings.py`` file::

	DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
	AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
	AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
	AWS_S3_REGION_NAME = 'eu-west-1'
	AWS_STORAGE_BUCKET_NAME = 'filepond-uploads'	
	AWS_DEFAULT_ACL = 'private'
	AWS_BUCKET_ACL = 'private'
	AWS_AUTO_CREATE_BUCKET = True

Note that the ACL for the bucket and the default ACL for files are set to
private. There may well be other security-related parameters that you will
want/need to set to ensure the security of the files on your chosen storage
backend. The configuration here provides an example but you should read the
*django-storages* docuemntation for your chosen backend and documentation
for the associated storage platform to ensure that you understand the
parameters that you are setting and any related potential security issues
that may result from your configuration. 

.. note:: django-storages is now included as a core dependency of 
	django-drf-filepond. However, the different django-storages backends 
	each have their own additional dependencies **which you need to install 
	manually** or add to your own app's dependencies. 
	
	You can add additional dependencies using ``pip`` by specifying the  
	optional *extras* feature tag, e.g. to install additional dependencies  
	required for django-storages ``boto3`` support run::
	
		pip install django-storages[boto3]
	
See ":ref:`Working with file uploads`" for more details on how to use the 
django-drf-filepond API to store files to a local or remote file store. 

.. note:: ``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` is not used when using
	a remote file store backend. It is recommended to remove this setting or
	leave it set to None.
	
	The base storage location for a remote file storage backend from
	django-storages is set using a setting specific to the backend that you
	are using - see the django-storages documentation for your chosen
	backend for further information.

.. _chunked_uploads:

Chunked uploads
===============

``django-drf-filepond`` now supports filepond
`chunked uploads <https://pqina.nl/filepond/docs/patterns/api/server/#chunk-uploads>`_.
To use chunked uploads, you enable the functionality in your configuration
of the filepond client and set the file chunk size you'd like to use. When
filepond attempts to upload a file larger than the chunk size, it breaks the
file up into chunks which are each uploaded in order. If the connection should
fail and a chunk doesn't upload correctly, the client will retry the chunk.
If the set number of retries is exceeded, the client stops attempting to
retry the upload but provides the user with a retry button to manually retry
the upload. ``django-drf-filepond`` includes all the necessary server-side
functionality to support this.

There is no configuration required for ``django-drf-filepond`` on the server
side to handle chunked uploads.

On the client side, you need to ensure that your 
`filepond configuration <https://pqina.nl/filepond/docs/patterns/api/filepond-instance/#server-configuration>`_
specifies server endpoints for both the ``process`` and ``patch`` methods
and that you have the required configuration options in place to enable
chunked uploads. For example, if you want to enable ``chunkUploads`` and
send uploads in 500,000 byte chunks, your filepond configuration should
include properties similar to the following::

    FilePond.setOptions({
        ...
        chunkUploads: true,
        chunkSize: 500000,
        server: {
            url: 'https://.../fp',
            process: '/process/',
            patch: '/patch/',
            ...
        }
        ...
    });


Advanced Configuration Options
==============================

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
=======

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
 