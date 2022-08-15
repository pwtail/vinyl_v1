
"""

ob.brands.all()
x(1, y=1).y(...)

"""
from vinyl import deferred


class LazyD:


    def __init__(self):
        self.ops = []

    def __getattr__(self, item):
        op = Getattr(item)
        self.ops.append(op)
        return self

    def __call__(self, *args, **kwargs):
        op = Call(args, kwargs)
        self.ops.append(op)
        return self

    def __get__(self, instance, owner):
        assert not self.ops
        op = Desc(instance, self.name)
        self.ops.append(op)
        return self

    async def _await(self):
        result = None
        async with deferred.driver():
            for op in self.ops:
                op.apply(result)
        return result
        #

    def __await__(self):
        return self._await().__await__()

    def __set_name__(self, owner, name):
        self.name = name


class Desc:
    def apply(self, result):
        assert result is None
