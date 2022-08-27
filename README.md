The vinyl project (aka async django)
---------------
*currently at alfa stage*

The vinyl project is an initiative (unofficial) to continue adding the 
async support to django. The main task is porting the **django orm** - the main 
remaining obstacle in the way.

Goals:
- async-only (native asynchrony)
- be compatible with django models, not break existing code
- be close to classic django in terms of API

**A model manager**

The main entry point to the magic is the model manager, which you need to 
add alongside 
the relular one (`objects`, likely).

```python
class M(models.Model):
  ...
  vinyl = VinylManager()
```

The default database for vinyl is `'vinyl_default'`. `vinyl` provides the 
respective backends. So, here is what you should have in the `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'PASSWORD': 'postgres',
        'USER': 'postgres',
        'NAME': 'mydb',
    },
    'vinyl_default': {
        'ENGINE': 'vinyl.postgresql_backend',
        'PASSWORD': 'postgres',
        'USER': 'postgres',
        'NAME': 'mydb',
    },
}
```

Now you can try the magic:

```python
await M.vinyl.all()
ob = await M.vinyl.get()
await ob.related_set.all()
ob.related_obj = related_obj
await ob.save()
```

`M.objects.all()` will keep working, like the rest of django.

**Model instances (aka the objects). How to do an insert**

Like django itself, vinyl builds a lot of its API around the model 
instances (CRUD operations, related attributes, etc). But since the API is 
different from django (namely, it is async), vinyl uses a different class for 
the model:

```
In [1]: (await M.vinyl.first()).__class__
Out[1]: vinyl.model.M
```

You can access the class of the vinyl model through `M.vinyl.model`, but 
generally you don't have to. With vinyl, you do not directly instantiate the 
models. When making a query, you get the instantiated objects already, and 
to create an object (make an insert) you should use `M.vinyl.create(**kwargs)`.
In other words, `await obj.save()` is used only for an update. As a side 
effect from separating an insert from an update, the saving code got much 
cleaner.

**Lazy attributes, prefetch_related and the like**

In django, the related attributes are lazy. If they have been prefetched 
somehow, you get the cached values, otherwise the query is made. In vinyl, 
lazy attributes are gone. For accessing the prefetched values you should use 
dictionary access:

```python
obj['related_obj']
obj['related_set']
```

Accessing the attribute will always make a query: `await obj.related_obj`. 
The once queried object will not be cached automatically.

Again, making the API more explicit is only a plus, in my opinion.

**Database drivers**

**Plans, directions**

