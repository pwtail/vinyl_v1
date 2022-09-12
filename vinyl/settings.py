from django.db import connections
from django.db.utils import load_backend

backends = {}

try:
    import django.db.backends.postgresql.base as postgresql
    backends[postgresql] = 'vinyl.backends.postgresql'
except:
    pass

try:
    import django.db.backends.mysql.base as mysql
    backends[mysql] = 'vinyl.backends.mysql'
except:
    pass


def replace_DATABASES(dic):
    for key, item in tuple(dic.items()):
        backend = load_backend(item['ENGINE'])
        if new_backend := backends.get(backend):
            item['ENGINE'] = new_backend
            del connections[key]