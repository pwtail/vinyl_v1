from django.db import router

from vinyl import deferred


class SaveMixin:
    #
    # # the single change is removed transaction
    # def save_base(
    #     self,
    #     raw=False,
    #     force_insert=False,
    #     force_update=False,
    #     using=None,
    #     update_fields=None,
    # ):
    #     using = using or router.db_for_write(self.__class__, instance=self)
    #     assert not (force_insert and (force_update or update_fields))
    #     assert update_fields is None or update_fields
    #     cls = origin = self.__class__
    #     # Skip proxies, but keep the origin as the proxy model.
    #     if cls._meta.proxy:
    #         cls = cls._meta.concrete_model
    #     meta = cls._meta
    #
    #     self._save_parents(cls, using, update_fields)
    #     self._save_table(
    #         raw,
    #         cls,
    #         force_insert,
    #         force_update,
    #         using,
    #         update_fields,
    #     )
    #     # Store the database on which the object was saved
    #     self._state.db = using
    #     # Once saved, this is no longer a to-be-added instance.
    #     self._state.adding = False
    #

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        """
        Always return True
        """
        filtered = base_qs.filter(pk=pk_val)
        if not values:
            return True
        filtered._update(values)
        return True

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
            if 'A' in str(parent):
                1
            if field:
                setattr(self, field.attname, self._get_pk_val(parent._meta))
                if field.is_cached(self):
                    field.delete_cached_value(self)

    # def _do_insert(self, manager, using, fields, returning_fields, raw):
    #     manager = self._model.vinyl
    #     return manager._insert(
    #         [self],
    #         fields=fields,
    #         returning_fields=returning_fields,
    #         using=using,
    #         raw=raw,
    #     )

    async def insert(self, using=None):
        self._prepare_related_fields_for_save(operation_name="save")
        using = using or router.db_for_write(self.__class__, instance=self)
        if not using.startswith('vinyl_'):
            using = f'vinyl_{using}'
        cls = origin = self._model
        # Skip proxies, but keep the origin as the proxy model.
        if cls._meta.proxy:
            cls = cls._meta.concrete_model
        meta = cls._meta

        # A transaction isn't needed if one query is issued.
        if meta.parents:
            await self._insert_parents(cls=cls, using=using)
        await self._insert_table(cls=cls, using=using)

