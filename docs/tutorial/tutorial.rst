Tutorial
===========

This tutorial will walk you through the process of creating a basic 
Django application that provides server-side functionality for 
`filepond <https://pqina.nl/filepond/>`_ using the `django-drf-filepond <https://github.com/ImperialCollegeLondon/django-drf-filepond>`_ app. 

A simple demo web page `filepond-jquery-example.html <https://github.com/ImperialCollegeLondon/django-drf-filepond/blob/master/docs/tutorial/filepond-jquery-example.html>`_ is provided for 
you to use as a test front-end for the demo Django application built in 
this tutorial. The web page uses filepond's jQuery adapter, loaded from a 
CDN, and is based on the `Bootstrap <https://getbootstrap.com/>`_ library's 
`starter template <https://getbootstrap.com/docs/4.1/examples/starter-template/>`_.

.. note:: This tutorial is in two parts:

	**Part A** focuses on setting up a simple Django application to demonstrate
	basic use of *django-drf-filepond*. It uses local file storage
	(via some form of locally mounted storage on the host server)
	for temporary uploads and stored files. 
	
	**Part B**, an advanced section at the end of the tutorial details the
	use of the remote file storage capabilities provided by
	*django-drf-filepond* via integration with the *django-storages* library.   

Tutorial Part A: Building a basic Django application that uses django-drf-filepond
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 

.. note:: **This tutorial assumes that you are using Python 3 and have** 
	`virtualenv <https://virtualenv.pypa.io/en/latest/>`_ **installed**

The tutorial will walk you through the following steps:

  1. Set up your environment - prepare an environment in which to undertake the tutorial
  2. Creating the Django application - create a simple django application configured to include the django-drf-filepond app
  3. Add the front-end demo web page
  4. Test the service

A1. Set up your environment
---------------------------

Create a directory in which to undertake this tutorial. For example, in 
your home directory, create the directory ``drf-filepond-tutorial``

We'll refer to this directory as ``${TUTORIAL_DIR}`` throughout the rest 
of the tutorial. If you're using a Linux or Mac OS platform with a bash 
shell (or a Windows-based environment that provides a bash shell such as 
`WSL <https://docs.microsoft.com/en-us/windows/wsl>`_) you can set the 
environment variable ``TUTORIAL_DIR`` to point the tutorial directory, for
example:

.. prompt:: bash
	
	export TUTORIAL_DIR=${HOME}/drf-filepond-tutorial

In ``${TUTORIAL_DIR}``, create a file named ``requirements.txt`` containing 
the following content::

	Django>=1.11
	django-drf-filepond


Now create a *virtualenv* in ``${TUTORIAL_DIR}``:

.. prompt:: bash

	virtualenv --prompt=drf-filepond-tutorial env
	source env/bin/activate

Your shell prompt should now have been modified to show 
``[drf-filepond-tutorial]`` which shows that you're within the virtual 
environment.

You can now install the dependencies:

.. prompt:: bash
	
	pip install -r requirements.txt


A2: Creating the Django application
-----------------------------------

In ``${TUTORIAL_DIR}`` with the virtualenv created in step 1 activated,
use the *django-admin* command to create a new django project:

.. prompt:: bash
	
	django-admin startproject drf_filepond_tutorial .

You should now see a ``manage.py`` file in your current directory as well as 
a ``drf_filepond_tutorial`` directory containing some Python source files.

As described in the Configuration section of the django-drf-filepond 
documentation, we'll now add the django-drf-filepond app to our Django 
project and then create the database to support this app and other default  
functionality within the Django project.

Open the file ``${TUTORIAL_DIR}/drf_filepond_tutorial/settings.py`` in an 
editor.

At the end of the ``INSTALLED_APPS`` section, add ``'django_drf_filepond'``::

	INSTALLED_APPS = [
		...
	    'django.contrib.staticfiles',
	    'django_drf_filepond',
	]

At the end of the file add a new configuration parameter::

	DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, 'filepond-temp-uploads')

Save and close the ``settings.py`` file. 

Now open the ``${TUTORIAL_DIR}/drf_filepond_tutorial/urls.py`` file.

After the two existing import statements, add a new import statement::

	from django.conf.urls import url, include
	
There should now be three import statements at the top of the ``urls.py`` 
file.

To the ``urlpatterns`` list, add an additional entry to link in the filepond 
server URLs such that the ``urlpatterns`` now look as follows::

	urlpatterns = [
    	    path('admin/', admin.site.urls),
    	    url(r'^fp/', include('django_drf_filepond.urls')),
	]

You can now create the database by running:

.. prompt:: bash
	
	python manage.py migrate


A3. Add the front-end demo web page
-----------------------------------

We now have a very basic, but fully-configured Django project that will act 
as a server for filepond. In order to test this, we need a filepond client.

The `filepond-jquery-example.html <https://github.com/ImperialCollegeLondon/django-drf-filepond/blob/master/docs/tutorial/filepond-jquery-example.html>`_ 
file in the ``docs/tutorial/`` directory of the `django-drf-filepond GitHub repository <https://github.com/ImperialCollegeLondon/django-drf-filepond>`_ 
provides a simple single-page filepond client using filepond's `jQuery adapter <https://github.com/pqina/jquery-filepond>`_.

We can now set up our Django project to serve this HTML file as a static 
file and use it to test the server-side filepond support.

**NOTE: This approach uses Django's** `static file serving support <https://docs.djangoproject.com/en/2.1/howto/static-files/#serving-static-files-during-development>`_ **and it should not be used for production deployment.** 

Create a directory called ``static`` in ${TUTORIAL_DIR}.

Place the ``filepond-jquery-example.html`` file in this directory.

Now open the ``${TUTORIAL_DIR}/drf_filepond_tutorial/urls.py`` file for 
editing. We'll add a new URL mapping to allow access to static files placed 
into the ``${TUTORIAL_DIR}/static/``. Add the following entry to the 
``urlpatterns`` list::


	url(r'^demo/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.BASE_DIR,'static')}),

You will also need to add 3 new import statements to the set of existing 
import statements::

	import os
	from django.views.static import serve
	from django.conf import settings

A4. Test the service
--------------------

You are now in a position to test the project that you've set up.

In the ``${TUTORIAL_DIR}`` directory, with the virtualenv that was created 
in step 1 activated, start the Django development server:

.. prompt:: bash

	python manage.py runserver


If there are any errors with your configuration, these will be shown in the 
terminal when you attempt to start the development server.

You should now be able to open the demo page in your browser. Point the 
browser to http://localhost:8000/demo/filepond-jquery-example.html and you 
should see the demo page shown in the figure below:

.. image:: images/filepond-demo-page.png

You can also test programmatically uploading a file from a remote URL. You 
can use your browser's developer console while on the django-drf-filepond 
demo page to call the filepond object's `addFile method <https://pqina.nl/filepond/docs/patterns/api/filepond-instance/#methods>`_ 
to get filepond to retrieve the file and add it. Place a test text file with 
some content in it into the ``${TUTORIAL_DIR}/static/`` directory. Call the 
file ``test.txt``.

In your browser console, enter the following JavaScript code:

.. code-block:: javascript

	testFile = null;
	result = $('.pond').filepond('addFile', 'http://localhost:8000/demo/test.txt').then(
		function(file) { testFile = file; }
	);
	
You will now see that the value of ``testFile.serverId`` contains the ID 
generated for the upload from the URL. The file upload should have appeared 
in the filepond panel in the webpage and it can be cancelled by clicking the 
cancel button in the UI in the same way as a file uploaded from the local 
system by browsing or drag and drop.

Tutorial Part B: Using remote file storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*django-drf-filepond*'s remote file storage enables you to place stored
uploads on different remote file stores. You can make use of any of the
`storage backends supported by django-storages <https://django-storages.readthedocs.io/en/latest/>`_.
This includes, for example, `Amazon S3 <https://aws.amazon.com/s3/>`_ or 
`Azure Storage <https://azure.microsoft.com/en-gb/services/storage/>`_.

This section of the tutorial assumes that you have completed part A and
builds on the deployed service developed there.
To support this part of the tutorial, a separate demo HTML page is provided.
This HTML file (`filepond-jquery-example-advanced.html <https://github.com/ImperialCollegeLondon/django-drf-filepond/filepond-jquery-example-advanced.html...>`_.)
includes a more advanced design to demonstrate the display of and subsequent
removal of stored uploads.

.. note:: Not all features detailed here are supported on all *django-storages*
	backends. Support depends directly on whether django-storages provides
	support for a given feature. For example, if django-storages doesn't
	support file deletion for a particular storage backend,
	*django-drf-filepond* will not support file deletion for that platform.

B1. Add a new interface and REST endpoint to the demo app
----------------------------------------------------------

Begin by updating the demo application that you set up in part A of
the tutorial with the more advanced HTML page, `filepond-jquery-example-advanced.html <https://github.com/ImperialCollegeLondon/django-drf-filepond/filepond-jquery-example-advanced.html...>`_,
that contains additional functionality. Obtain the file directly from GitHub, 
or copy it from your clone of the *django-drf-filepond* repository into the 
``${TUTORIAL_DIR}/static/`` directory.

*django-drf-filepond* directly handles the filepond ``process`` endpoint that
is used for temporary file uploads. When the form containing the filepond
component is submitted, this will be handled by your application rather than
by *django-drf-filepond*. In the case of this tutorial, the *drf_filepond_tutorial*
app needs to handle the submission of the form that triggers the permanent
storage of the file upload. 

``filepond-jquery-example-advanced.html`` contains an HTML form in which the
filepond component is embedded. When a file is added to filepond, it is
uploaded as a temporary upload. Clicking the "Store uploads" button triggers
submission of the form. This form submission is handled by a view in the
*drf_filepond_tutorial* app. In part A of the tutorial, there were no views
within the *drf_filepond_tutorial* app itself. File uploads were handled by
the views provided by *django-drf-filepond*. We now need a view in
the *drf_filepond_tutorial* app to handle the form submission. A ``views.py``
file is provided in the ``docs/tutorial`` directory of the *django-drf-filepond*
repository.

Copy ``docs/tutorial/views.py`` and place it in ``${TUTORIAL_DIR}/drf_filepond_tutorial/``.

It is now necessary to modify ``${TUTORIAL_DIR}/drf_filepond_tutorial/urls.py``
to link an endpoint URL to the form processing view in ``views.py``. Add the 
following entry to the ``urlpatterns`` list in ``urls.py``:

.. code-block:: python

			url(r'^submitForm/$', views.SubmitFormView.as_view(), name='submit_form'),

B2. Configure your storage backend
-----------------------------------

It is now necessary to add configuration for a storage backend. If one is
not configured, *django-drf-filepond* will assume that you are using local
file storage and set itself up to use the location specified by the
``DJANGO_DRF_FILEPOND_FILE_STORE_PATH`` parameter in the demo application's
settings file which can be found at ``${TUTORIAL_DIR}/drf_filepond_tutorial/settings.py``

For the example here, we'll use the Amazon S3 storage backend in *django-storages*
to talk to the open source, Amazon S3 compatible `MinIO <https://min.io/>`_
storage service. You can download and run MinIO within a docker container
on your local system or you can use the same approach detailed here to target
Amazon S3 directly.

To begin with, it will be necessary to add additional dependencies required
by *django-storages* and to set a number of configuration parameters in the
demo application's ``${TUTORIAL_DIR}/drf_filepond_tutorial/settings.py``
file.

*django-storages* has a number of optional dependencies that may be required
depending on the storage backend that you are using. boto3




If you have stopped the Django development server that was started in part A
of the tutorial, you should restart it now by running the following in a shell
in the ``${TUTORIAL_DIR}`` directory:

.. prompt:: bash

	python manage.py runserver



Clicking the "Store uploads" button in the web page submits the form
content (containing one or more unique IDs representing filepond temporary
uploads) to the web application's `/submitForm` URL and this will then be
handled by the relevant function in the view class.
