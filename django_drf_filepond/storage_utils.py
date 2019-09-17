import importlib
import logging


LOG = logging.getLogger(__name__)


def _get_storage_backend(fq_classname):
    """
    Load the specified django-storages storage backend class. This is called
    regardless of whether a beckend is specified so if fq_classname is not
    set, we just return None.

    fq_classname is a string specifying the fully-qualified class name of
    the django-storages backend to use, e.g.
        'storages.backends.sftpstorage.SFTPStorage'
    """
    LOG.debug('Running _get_storage_backend with fq_classname [%s]'
              % fq_classname)

    if not fq_classname:
        return None

    (modname, clname) = fq_classname.rsplit('.', 1)
    # A test import of the backend storage class should have been undertaken
    # at app startup in django_drf_filepond.apps.ready so any failure
    # importing the backend should have been picked up then.
    mod = importlib.import_module(modname)
    storage_backend = getattr(mod, clname)()
    LOG.info('Storage backend instance [%s] created...' % fq_classname)

    return storage_backend
