"""FilePond server-side URL configuration

Based on the server-side configuration details
provided at:
https://pqina.nl/filepond/docs/patterns/api/server/#configuration
"""
import six
if six.PY2:
    from django.conf.urls import url
else:
    from django.urls import re_path, path
from django_drf_filepond.views import ProcessView, RevertView, LoadView,\
     RestoreView, FetchView, PatchView

#############################################################################
# PYTHON 2 SUPPORT
# Retaining Python 2 compatibility for now. However, with the switch to
# Django 4.0, django.conf.urls.url has been removed and we need to switch
# to paths - this Python 2 specific block will ultimately be removed when
# Python 2.7 support is dropped along with support for django 1.x.
#
# django-drf-filepond SUPPORT FOR PYTHON 2.7/DJANGO 1.11 WILL BE DEPRECATED
# IN RELEASE 0.5.0. THIS WILL BE THE LAST RELEASE TO SUPPORT PYTHON 2.7.
#############################################################################
if six.PY2:
    urlpatterns = [
        url(r'^process/$', ProcessView.as_view(), name='process'),
        url(r'^patch/(?P<chunk_id>[0-9a-zA-Z]{22})$', PatchView.as_view(),
            name='patch'),
        url(r'^revert/$', RevertView.as_view(), name='revert'),
        url(r'^load/$', LoadView.as_view(), name='load'),
        url(r'^restore/$', RestoreView.as_view(), name='restore'),
        url(r'^fetch/$', FetchView.as_view(), name='fetch')
    ]
else:
    urlpatterns = [
        path('process/', ProcessView.as_view(), name='process'),
        re_path(r'^patch/(?P<chunk_id>[0-9a-zA-Z]{22})$', PatchView.as_view(),
                name='patch'),
        path('revert/', RevertView.as_view(), name='revert'),
        path('load/', LoadView.as_view(), name='load'),
        path('restore/', RestoreView.as_view(), name='restore'),
        path('fetch/', FetchView.as_view(), name='fetch')
    ]
