from django.db import models
from simple_django_htmx import views


class HXRequestViews(models.TextChoices):
    CREATE_UPDATE = views.HtmxCreateUpdateView
    # TEMPLATE =vi
