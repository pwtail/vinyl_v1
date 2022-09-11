# NOT USED

from django.db.utils import load_backend

from vinyl.flags import is_vinyl

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


def _DATABASES(dic):
    for key, item in dic.items():
        backend = load_backend(item['ENGINE'])
        if b := backends.get(backend):
            backend._vinyl_backend = b

    return DatabaseDict(dic)


class DatabaseDict(dict):

    def __getitem__(self, item):
        value = super().__getitem__(item)
        if item != 'ENGINE':
            return value
        if is_vinyl.get():
            return value._vinyl_backend
        return value