import importlib
import inspect
from django.apps import apps
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from typing import Any, Dict
import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie


from simple_django_htmx.utils import deserialize_kwargs, is_htmx_request
from django.conf import settings


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
            hx_request.kwargs = self.get_extra_kwargs(request)
            return hx_request.get(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if is_htmx_request(request):
            # Call get to setup neccessary parts for the context
            super().get(request, *args, **kwargs)
            hx_request = self.get_hx_request(request)
            hx_request.view = self
            hx_request.kwargs = self.get_extra_kwargs(request)
            return hx_request.post(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def get_hx_request(self, request):
        hx_request_name = request.GET.get("hx_request_name")
        hx_reqeusts = self.get_hx_reqeust_classes()
        hx_request = next(
            hx_request
            for name, hx_request in hx_reqeusts.items()
            if name == hx_request_name
        )
        return hx_request()

    def get_hx_reqeust_classes(self):
        from .hx_requests import HXRequest

        modules = []
        hx_request_classes = {}
        for app in apps.get_app_configs():
            if app.label != __package__:
                try:
                    modules.append(importlib.import_module(f"{app.label}.hx_requests"))
                except ModuleNotFoundError:
                    pass
        for module in modules:
            clsmembers = inspect.getmembers(module, inspect.isclass)
            for _, obj in clsmembers:
                if issubclass(obj, HXRequest) and getattr(obj, "name", None):
                    hx_request_classes[obj.name] = obj
        return hx_request_classes

    def get_extra_kwargs(self, request):
        kwargs = {}
        for key in request.GET:
            kwargs[key] = request.GET.get(key)

        return deserialize_kwargs(**kwargs)


class MessagesMixin:
    show_messages: bool = getattr(settings, "HX_REQUESTS_SHOW_MESSAGES", False)
    success_message: str = ""
    error_message: str = ""

    def get_success_message(self, request, **kwargs) -> str:
        return self.success_message

    def get_error_message(self, request, **kwargs) -> str:
        return self.error_message

    def setup_header_for_messages(self, message, level) -> Dict:
        return (
            {
                "HX-Trigger": json.dumps(
                    {"showMessages": {"message": message, "level": level}}
                )
            }
            if self.show_messages
            else {}
        )
