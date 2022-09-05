The vinyl project
---------------
*currently at alfa stage*

The purpose of vinyl project is to add the async support to django orm.
It takes rather radical approach, providing both async and sync versions 
at the same time:

```
pip install vinyl_async  # to install the async version
pip install vinyl_sync   # to install the sync one
```

The pip commands are shown just for an example, vinyl won't be updated on PyPI 
very frequently in the nearest future, so please use the repository.

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

**How is this possible?**

First of all, not all of django is rewritten. Querysets are lazy and can be 
made 
awaitable relatively easy. Then there is a lot of write-only functionality, 
when you execute statements but don't need to fetch the result. These can be 
accumulated in a list and then executed at the end, thus removing the need 
for a rewrite.

Next, the sync version is actually generated from the async one. I thought 
that, following some rules, the sync version can be obtained by a static 
tranform. Currently, even that is not required, as the transform is just 
find-and-replace ([transform.py](https://github.com/vinylproject/vinyl/blob/master/transform.py)).
The sync version lives in [vinyl_sync](https://github.com/vinylproject/vinyl/tree/master/vinyl_sync)
directory.

A few words about drivers and backends. A vinyl backend provides both sync and 
async modes. The [psycopg3](https://github.com/psycopg/psycopg) was the 
simplest to use, as it provides both sync and async API. Even more than that,
I used the connection pool (psycopg_pool) for the sync version too. The pool 
for that case has 
the size equal to 1. Because the main logic - the lifetime of a connection, 
when to invalidate one, how to initialize it - is actually the same. For 
mysql, I actually didn't touch it's sync version and just added the async 
one (I told you it is supported worse).

**Closing note**

Actually vinyl has all rights to become the next version of django. Because 
it keeps the compatibility with the latter, provides async functionality, 
and is developed as a single codebase. It even allows to make changes in a 
compatible way, being encapsulated in a model manager. It doesn't force user to 
make his service async-only, allowing for half-sync / half-async applications.

Currently, the sync version has as many bugs as the async one does. And is 
going to stay that way. There is no rush with it, as you can always use 
vanilla django for the sync endpoints. However, for the longer perspective - 
it is exactly what is needed.