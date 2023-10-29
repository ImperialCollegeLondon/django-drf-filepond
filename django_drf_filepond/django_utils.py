###########################################################################
# Django's content_disposition_header function, as included in Django 4.2
# The function is being reproduced here with modifications to support it's 
# use with earlier versions of Django. 
# The original code is available at:
# https://docs.djangoproject.com/en/4.2/_modules/django/utils/http/#content_disposition_header
# and via github in the django.utils.http module:
# https://github.com/django/django/blob/main/django/utils/http.py#L357
# The original code on which the function below is base is released under a
# BSD-3-Clauselicence and is Copyright (c) Django Software Foundation and
# individual contributors; All Rights Reserved; See Django LICENSE file at:
# https://github.com/django/django/blob/main/LICENSE
###########################################################################
from urllib.parse import quote

def content_disposition_header(as_attachment, filename):
    """
    Construct a Content-Disposition HTTP header value from the given filename
    as specified by RFC 6266.
    """
    if filename:
        disposition = "attachment" if as_attachment else "inline"
        try:
            filename.encode("ascii")
            file_expr = 'filename="{}"'.format(
                filename.replace("\\", "\\\\").replace('"', r"\"")
            )
        except UnicodeEncodeError:
            file_expr = "filename*=utf-8''{}".format(quote(filename))
        return ("%s; %s" % (disposition, file_expr))
    elif as_attachment:
        return "attachment"
    else:
        return None
###########################################################################
# End of Django code
###########################################################################
