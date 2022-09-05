The vinyl project
---------------
*currently at alfa stage*

The purpose of vinyl project is to add the async support to django orm.
It takes rather radical approach and provides both async and sync versions 
at the same time:

```
pip install vinyl_async  # to install the async version
pip install vinyl_sync   # to install the sync one
```

The sync and async version mirror each other in terms of the API. The latter 
is very close to that of Django, but introduces some changes as well.

**A model manager**

The entire functionality of vinyl is encapsulated in a model manager. This 
makes possible for vinyl to introduce incompatible changes, because the old 
functionality remains available. For example:

```python
class M(models.Model):
    vinyl = VinylManager(using='db_with_vinyl_backend')
    # objects = VinylManager()
```

Suppose we are using the sync version of vinyl. `M.objects.all()` will use 
plain old django, and `M.vinyl.all()` will use vinyl - the results will be 
the same. If you uncomment the last line than you will overwrite 
the old implementation.

Vinyl provides its own backends:

```python
DATABASES = {
    'vinyl_db': {
        'ENGINE': 'vinyl.postgresql_backend',
        'PASSWORD': 'postgres',
        'USER': 'postgres',
        'NAME': 'mydb',
    },
}
```

Currently postgresql and mysql(mariadb) are supported, the first being 
supported better than the second. More than one provider is needed mainly to 
correctly define the interface of a backend.

The API is what you would expect:

```python
await M.vinyl.all()  # async for also works
ob = await M.vinyl.get()
await ob.related_set.all()
ob.related_obj = related_obj
await ob.save()
```

**The changes**

As I said, some deliberate changes are made. The main one: the lazy 
attributes are gone. `obj.related_attr` is always eager, i. e., hits the 
database. If the attribute has been prefetched and no query is needed, than 
use `obj['related_attr']`. I think, the explicit approach is better, and 
also it better fits the async version (in which you should call `await obj.
related_obj` and `obj['related_obj']` respectively).

There are other changes as well:

- no signals
- no chunked fetching
- autocommit is turned off
