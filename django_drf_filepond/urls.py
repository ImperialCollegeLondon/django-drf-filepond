"""FilePond server-side URL configuration

Based on the server-side configuration details
provided at:
https://pqina.nl/filepond/docs/patterns/api/server/#configuration
"""
from django.urls import path, re_path
from django_drf_filepond.views import ProcessView, RevertView, LoadView,\
     RestoreView, FetchView, PatchView

urlpatterns = [
    path('process/', ProcessView.as_view(), name='process'),
    re_path(r'^patch/(?P<chunk_id>[0-9a-zA-Z]{22})$', PatchView.as_view(),
            name='patch'),
    path('revert/', RevertView.as_view(), name='revert'),
    path('load/', LoadView.as_view(), name='load'),
    path('restore/', RestoreView.as_view(), name='restore'),
    path('fetch/', FetchView.as_view(), name='fetch')
]
