**The vinyl project (aka async django)**

The vinyl project is an initiative (unofficial though) to continue adding the 
async support to django. The main task is porting the django orm - the main 
remaining obstacle in the way. Yes, you've 
been waiting for this.

Goals:
- async-only (native asynchrony)
- be compatible with django models, not break existing code
- be close to classic django in terms of API

*currently vinyl is at alfa stage*

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

**Async-only**

However doesn't break code and is similar

**Insert**

**Lazy attributes, prefetch_related and the like**

**d**

**Database support**

**Plans, directions**

**Status: alfa**