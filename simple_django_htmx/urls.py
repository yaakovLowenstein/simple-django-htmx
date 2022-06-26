from django.urls import include, path

from . import views


urlpatterns = [
    path("htmx/<int:pk>", views.HtmxView.as_view(), name="htmx"),
    path("htmx/", views.HtmxView.as_view(), name="htmx"),
]
