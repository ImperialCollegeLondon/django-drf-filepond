Introduction
============

`django-drf-filepond <https://github.com/ImperialCollegeLondon/django-drf-filepond>`_ 
is a `Django <https://www.djangoproject.com/>`_ app providing a back-end 
implementation for `pqina <https://github.com/pqina/>`_'s excellent 
`filepond <https://pqina.nl/filepond/>`_ file upload library. 

django-drf-filepond can be easily added to your Django applications to provide
support for handling file uploads from a filepond client. The app includes
support for filepond's ``process``, ``patch``, ``revert``, ``fetch``,
``restore`` and ``load`` endpoints allowing all the core file upload functions
of the library to be used.

django-drf-filepond provides support for managing the storage of files once
they have been uploaded using filepond so that they can subsequently be
accessed using filepond's ``load`` endpoint.

Support is provided for storage on remote storage backends via integration
with the `django-storages <https://django-storages.readthedocs.io/en/latest/>`_
library.

Support is also provided for filepond's chunked file upload, functionality.
