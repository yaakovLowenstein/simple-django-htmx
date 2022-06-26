from typing import Dict
from django import template

from simple_django_htmx.utils import get_csrf_token, get_url

register = template.Library()


@register.simple_tag(takes_context=True)
def render_hx(context:Dict, hx_request_name:str, method:str="get", object=None, **kwargs)->str:
    """
    Renders out the hx-post or hx-get with the correct url along with all kwargs
    turned into GET params.
    """
    url = get_url(context, hx_request_name, object, **kwargs)

    token = get_csrf_token(context)
    return f""" hx-{method}={url}  
                hx-headers={{"X-CSRFTOKEN":"{token}"}} 
            """
