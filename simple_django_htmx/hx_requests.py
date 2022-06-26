from typing import Dict
from django.forms import Form

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.apps import apps
from django.conf import settings
from django.contrib.messages import get_messages


class HXRequest:
    """
    HXRequest is the base class for Htmx requests.
    """

    name: str
    GET_template: str
    POST_template: str
    hx_object_name:str = "hx_object"

    def get_context_data(self, **kwargs)->Dict:
        context = self.view.get_context_data(**kwargs)
        context.update(**kwargs)
        context[self.hx_object_name] = self.hx_object
        context["request"] = self.request
        context["hx_request"] = self
        return context

    def get_hx_object(self, request):
        if request.GET.get("object"):
            serialized_hx_object = request.GET.get("object")
            app_label, model, pk = serialized_hx_object.split("_")
            model = apps.get_model(app_label, model)
            return model.objects.get(pk=pk)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.setup_hx_request(request)
        context = self.get_context_data(**kwargs)
        html = render_to_string(self.GET_template, context, request)
        return HttpResponse(html)

    def setup_hx_request(self, request):
        if not hasattr(self, "hx_object"):
            self.hx_object = self.get_hx_object(request)
        self.request = request


class FormHXRequest(HXRequest):
    """
    Adds in form to context.
    On POST if the form is valid returns form_valid OR the POST_template.
    If the form is invalid returns form_invalid or the GET_template.

    form_invalid and form_valid can be overriden for custom behavior.
    Can override get_template_kwargs to add custom kwargs into the form.
    """

    form_class: Form

    def get_context_data(self, **kwargs)->Dict:
        context = super().get_context_data(**kwargs)
        context["form"] = self.form
        return context

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.setup_hx_request(request)
        self.form = self.form_class(**self.get_form_kwargs(**kwargs))
        context = self.get_context_data(**kwargs)
        return super().get(request, context, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.setup_hx_request(request)
        self.form = self.form_class(**self.get_form_kwargs(**kwargs))

        if self.form.is_valid():
            response = self.form_valid(self.form, self.request, **kwargs)
            context = self.get_context_data(**kwargs)
            html = render_to_string(self.POST_template, context, request)
            return response or HttpResponse(html)
        else:
            context = self.get_context_data(**kwargs)
            html = render_to_string(self.GET_template, context, request)
            return self.form_invalid(self.form, self.request, **kwargs) or HttpResponse(
                html
            )

    def form_valid(self, form, request, **kwargs):
        form.save()

    def form_invalid(self, form, request, **kwargs):
        pass

    def get_form_kwargs(self, **kwargs):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {"initial": self.get_initial()}

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        if hasattr(self, "hx_object"):
            kwargs.update({"instance": self.hx_object})
        return kwargs

    def get_initial(self):
        return {}


class DeleteHXRequest(HXRequest):
    """
    HXRequest for deleting objects. Can override handle_delete
    for custom behavior.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.setup_hx_request(request)
        response = self.handle_delete(self.request, **kwargs)

        context = self.get_context_data(**kwargs)
        html = render_to_string(self.POST_template, context, request)
        return response or HttpResponse(html)

    def handle_delete(self, request, **kwargs):
        self.hx_object.delete()
