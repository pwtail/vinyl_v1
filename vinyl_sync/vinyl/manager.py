from django.db import DEFAULT_DB_ALIAS
from django.db.models.manager import BaseManager
from django.dispatch import receiver

from vinyl.meta import make_vinyl_model
from vinyl.queryset import VinylQuerySet
from vinyl.signals import models_ready


class VinylManager(BaseManager.from_queryset(VinylQuerySet)):
    """
    VinylManager itself.
    """
    model = None

    def __init__(self, *, using=DEFAULT_DB_ALIAS):
        super().__init__()
        self._db = using

    def _create_model(self, django_model, *args, **kw):
        self.manager.model = make_vinyl_model(django_model)

    def contribute_to_class(self, owner, name):
        super().contribute_to_class(owner, name)

        @receiver(models_ready)
        def create_model(**kwargs):
            self.django_model = owner
            self.model = make_vinyl_model(owner)
