def unused(f):
    def wrapper(*args, **kw):
        assert False
    return wrapper


class Unused:

    def _forbid(self, instance):
        classname = f'{instance.__class__.__module__}.{instance.__class__.__name__}'
        assert False, (
            f"Called {classname}.{self.name}"
        )

    def __get__(self, instance, owner):
        return lambda *args, **kw: self._forbid(instance)

    def __set_name__(self, owner, name):
        self.name = name