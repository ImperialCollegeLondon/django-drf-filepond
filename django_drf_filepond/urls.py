"""FilePond server-side URL configuration

Based on the server-side configuration details
provided at: 
https://pqina.nl/filepond/docs/patterns/api/server/#configuration
"""
from django.conf.urls import url
from django_drf_filepond.views import ProcessView, RevertView, LoadView,\
     RestoreView, FetchView

urlpatterns = [
    url(r'^process/$', ProcessView.as_view(), name='process'),
    url(r'^revert/$', RevertView.as_view(), name='revert'),
    url(r'^load/$', LoadView.as_view(), name='load'),
    url(r'^restore/$', RestoreView.as_view(), name='restore'),
    url(r'^fetch/$', FetchView.as_view(), name='fetch')
]
