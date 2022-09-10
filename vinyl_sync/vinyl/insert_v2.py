from django.db import models

from vinyl.model import SkipModelBase


class Saving(models.Model, metaclass=SkipModelBase):

    def get_pro(self):
        def extend_parents(cls, result=[]):
            meta = cls._meta
            for parent, field in meta.parents.items():
                # Make sure the link fields are synced between parent and self.
                extend_parents(parent, result)
                # result.extend(parents)
                # result.append(parent)
            result.append(cls)
            return result

        return extend_parents(self.__class__)

    # iterator
    def _(self):
        for parent, field in meta.parents.items():
            # Make sure the link fields are synced between parent and self.
            with choose_parent():
                yield
            # Set the parent's PK value to self.
            if field:
                setattr(self, field.attname, self._get_pk_val(parent._meta))



    def choose_parent(self, cls):
        def _save_table(_super=self._save_table):
            1
            # pass only cls
            return True
        try:
            parents = cls._meta.parents
            cls._meta.parents = ()
            yield
        finally:
            cls._meta.parents = parents

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        for cls in self.get_pro():
            with self.choose_parent(cls):
                with self._deferred():
                    models.Model.save(
                        self, force_insert=force_insert, force_update=force_update,
                        using=using, update_fields=update_fields
                    )