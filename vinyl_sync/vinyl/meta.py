from django.db.models.query_utils import DeferredAttribute

from vinyl.model import VinylModel, DeferredModel


def make_vinyl_model(model):
    if hasattr(model, 'vinyl_model'):
        return model.vinyl_model
    ns = _copy_namespace(model)
    newcls = model.vinyl_model = type(model.__name__, (VinylModel, model), ns)
    newcls._deferred_model = type(model.__name__, (DeferredModel, model), {})
    return newcls


def _copy_namespace(model):
    ns = {}
    model_vars = {
        field.name: getattr(model, field.name)
        for field in model._meta.fields
    }
    model_vars.update(vars(model))
    parent_fields = set(model._meta.parents.values())
    for key, val in model_vars.items():
        if (field := getattr(val, 'field', None)) and val.__module__ == 'django.db.models.fields.related_descriptors':
            if field in parent_fields:
                continue
            if isinstance(val, DeferredAttribute):
                continue
            if hasattr(val, 'rel_mgr') or hasattr(val, 'related_manager_cls'):
                from vinyl.descriptors import RelatedManagerDescriptor
                val = RelatedManagerDescriptor(val)
            else:
                from vinyl.descriptors import FKDescriptor
                val = FKDescriptor(val)
            ns[key] = val
        # if isinstance(val, Man)
    return ns