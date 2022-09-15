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

#BUGG

def _DATABASES(dic):
    # dic = settings.DATABASES
    for key, item in tuple(dic.items()):
        backend = load_backend(item['ENGINE'])
        if new_backend := backends.get(backend):
            dic[f'vinyl_{key}'] = (new_item := dict(item))
            new_item['ENGINE'] = new_backend

    return dic
