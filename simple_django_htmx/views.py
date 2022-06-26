from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View, TemplateView
from typing import Any, Dict
from django.template.loader import render_to_string

from django.views.generic.edit import UpdateView
from simple_django_htmx.mixins import HtmxViewMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie


from simple_django_htmx.utils import deserialize_kwargs, is_htmx_request

# Create your views here.
class CreateUpdateView(UpdateView):
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None


class HtmxView(View):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HtmxVIewMixin(View):
    """
    Mixin to be added to views that are using HXRequests.
    Hijacks the get and post to route them to the proper
    HXReqeust.
    """

    hx_requests: Dict = []

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if is_htmx_request(request):
            super().get(request, *args, **kwargs)
            hx_request = self.get_hx_request(request)
            hx_request.view = self
            kwargs.update(self.get_extra_kwargs(request))
            return hx_request.get(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if is_htmx_request(request):
            # Call get to setup neccessary parts for the context
            super().get(request, *args, **kwargs)
            hx_request = self.get_hx_request(request)
            hx_request.view = self
            kwargs.update(self.get_extra_kwargs(request))
            return hx_request.post(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def get_hx_request(self, request):
        hx_request_name = request.GET.get("hx_request_name")
        hx_request = next(
            hx_request
            for hx_request in self.hx_requests
            if hx_request.name == hx_request_name
        )
        return hx_request()

    def get_extra_kwargs(self, request):
        kwargs = {}
        for key in request.GET:
            kwargs[key] = request.GET.get(key)

        return deserialize_kwargs(**kwargs)
