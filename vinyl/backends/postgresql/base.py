# pragma: i/o specific
from vinyl.flags import is_async

if is_async():
    from .asyn import DatabaseWrapper
else:
    from .sync import DatabaseWrapper

assert DatabaseWrapper