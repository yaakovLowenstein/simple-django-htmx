from typing import Dict
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.apps import apps
from simple_django_htmx.views import MessagesMixin


class HXRequest:
    """
    HXRequest is the base class for Htmx requests.
    """

    name: str = ""
    GET_template: str = ""
    POST_template: str = ""
    hx_object_name: str = "hx_object"

    def get_context_data(self, **kwargs) -> Dict:
        context = self.view.get_context_data(**kwargs)
        context["hx_kwargs"] = self.kwargs
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
        return HttpResponse(html, headers=self.get_GET_headers(**kwargs))

    def setup_hx_request(self, request):
        self.request = request
        if not hasattr(self, "hx_object"):
            self.hx_object = self.get_hx_object(request)

    def get_GET_headers(self, **kwargs) -> Dict:
        return {}


class FormHXRequest(HXRequest, MessagesMixin):
    """
    Adds in form to context.
    On POST if the form is valid returns form_valid OR the POST_template.
    If the form is invalid returns form_invalid or the GET_template.

    form_invalid and form_valid can be overriden for custom behavior.
    Can override get_template_kwargs to add custom kwargs into the form.
    """

    form_class: Form
    _is_valid: bool

    def get_context_data(self, **kwargs) -> Dict:
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
            context = self.get_context_data(**kwargs)
            response = self.form_valid(self.form, self.request, context, **kwargs)
            message, level = self.get_success_message(request, **kwargs), "success"

        else:
            context = self.get_context_data(**kwargs)
            response = self.form_invalid(self.form, self.request, context, **kwargs)
            message, level = self.get_error_message(request, **kwargs), "danger"

        return HttpResponse(
            response,
            headers=self.get_POST_headers(message=message, level=level, **kwargs),
        )

    def form_valid(self, form, request, context, **kwargs) -> str:
        form.save()
        return render_to_string(self.POST_template, context, request)

    def form_invalid(self, form, request, context, **kwargs) -> str:
        return render_to_string(self.GET_template, context, request)

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

    def get_success_message(self, request, **kwargs) -> str:
        return (
            self.success_message
            or f"{self.hx_object._meta.model.__name__.capitalize()} saved successfully."
        )

    def get_error_message(self, request, **kwargs) -> str:
        return (
            self.error_message
            or f"{self.hx_object._meta.model.__name__.capitalize()} did not save successfully."
        )

    def get_POST_headers(self, **kwargs) -> Dict:
        headers = {}
        headers.update(
            **self.setup_header_for_messages(kwargs.get("message"), kwargs.get("level"))
        )
        return headers


class DeleteHXRequest(HXRequest, MessagesMixin):
    """
    HXRequest for deleting objects. Can override handle_delete
    for custom behavior.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.setup_hx_request(request)
        context = self.get_context_data(**kwargs)
        response = self.handle_delete(self.request, context, **kwargs)
        message, level = self.get_success_message(request, **kwargs), "success"
        return HttpResponse(
            response,
            headers=self.get_POST_headers(message=message, level=level, **kwargs),
        )

    def handle_delete(self, request, context, **kwargs) -> str:
        self.hx_object.delete()
        return render_to_string(self.POST_template, context, request)

    def get_success_message(self, request, **kwargs) -> str:
        return (
            self.success_message
            or f"{self.hx_object._meta.model.__name__.capitalize()} deleted successfully."
        )

    def get_POST_headers(self, **kwargs) -> Dict:
        headers = {}
        headers.update(
            **self.setup_header_for_messages(kwargs.get("message"), kwargs.get("level"))
        )
        return headers
