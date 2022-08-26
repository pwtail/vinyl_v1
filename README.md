The vinyl project (aka async django)

The vinyl project is an initiative (unofficial though) to add native async 
support to django. Currently, the vinyl python package adds the async 
support to the django orm, 
the main remaining obstacle on the way to making django async. Yes, you've 
been waiting for this.

currently - alfa stage

**A plugin**

This is a third-party package that, once installed, adds async capabilities 
to your django project. It doesn't break your existing code. Its main entity is 
the `VinylManager` class, which is, as you could guess, a model manager.

```python


class M(models.Model):
  ...
  vinyl = VinylManager()
```

rflkerfmlw

```python
await M.vinyl.all()
ob = await M.vinyl.get()
await ob.related_set
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