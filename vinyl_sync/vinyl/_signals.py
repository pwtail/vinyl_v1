import inspect
from django.dispatch import Signal

models_ready = Signal()


def get_declared_signals(mod):
    ns = {}
    for k, v in vars(mod):
        if isinstance(v, Signal):
            ns[k] = v
    return ns


class SignalPatch:

    @classmethod
    def apply(cls):
        Signal.__init__ = SignalPatch.__init__
        Signal.send = SignalPatch.send

    def __init__(self, *args, __init__=Signal.__init__, **kwargs):
        __init__(self, *args, **kwargs)
        self._declared_in_module = inspect.getmodule(inspect.currentframe().f_back)

    def send(self, *args, send=Signal.send, **kwargs):
        send(self, *args, **kwargs)
        if not hasattr(self, 'name'):
            self.name = SignalPatch.get_name(self)
        print(self.name)

    def get_name(self):
        if not hasattr(m := self._declared_in_module, '_declared_signals'):
            m._declared_signals = get_declared_signals(m)
        for name, val in m._declared_signals:
            if val is self:
                return name
        assert False