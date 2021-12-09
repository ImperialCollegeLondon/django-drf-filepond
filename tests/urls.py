"""tests URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
import six
if six.PY2:
    from django.conf.urls import url
else:
    from django.urls import re_path
from django.conf.urls import include

from django.conf import settings

if six.PY2:
    urlpatterns = [
        # path('admin/', admin.site.urls),
        url(settings.URL_BASE, include('django_drf_filepond.urls'))
    ]
else:
    urlpatterns = [
        # path('admin/', admin.site.urls),
        re_path(settings.URL_BASE, include('django_drf_filepond.urls'))
    ]
