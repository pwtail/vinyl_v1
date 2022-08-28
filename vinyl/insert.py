from django.db import router


class InsertMixin:

    async def _insert_table(self, cls, using=None):
        meta = cls._meta
        pk_val = self._get_pk_val(meta)
        if pk_val is None:
            pk_val = meta.pk.get_pk_value_on_save(self)
            setattr(self, meta.pk.attname, pk_val)
        pk_set = pk_val is not None
        fields = meta.local_concrete_fields
        if not pk_set:
            fields = [f for f in fields if f is not meta.auto_field]

        returning_fields = meta.db_returning_fields

        results = await self._do_insert(
            cls._base_manager, using, fields, returning_fields, raw=False
        )
        if results:
            for value, field in zip(results[0], returning_fields):
                setattr(self, field.attname, value)

    async def _insert_parents(self, cls, using):
        meta = cls._meta
        for parent, field in meta.parents.items():
            # Make sure the link fields are synced between parent and self.
            if (
                field
                and getattr(self, parent._meta.pk.attname) is None
                and getattr(self, field.attname) is not None
            ):
                setattr(self, parent._meta.pk.attname, getattr(self, field.attname))
            await self._insert_parents(
                cls=parent, using=using
            )
            await self._insert_table(cls=parent, using=using)
            # Set the parent's PK value to self.
            if field:
                setattr(self, field.attname, self._get_pk_val(parent._meta))
                if field.is_cached(self):
                    field.delete_cached_value(self)

    async def insert(self, using=None):
        self._prepare_related_fields_for_save(operation_name="save")
        using = using or router.db_for_write(self.__class__, instance=self)
        if not using.startswith('vinyl_'):
            using = f'vinyl_{using}'
        cls = self._model
        # Skip proxies, but keep the origin as the proxy model.
        if cls._meta.proxy:
            cls = cls._meta.concrete_model
        meta = cls._meta

        # A transaction isn't needed if one query is issued.
        if meta.parents:
            await self._insert_parents(cls=cls, using=using)
        await self._insert_table(cls=cls, using=using)

