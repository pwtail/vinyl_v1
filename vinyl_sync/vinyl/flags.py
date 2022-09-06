import inspect


def hi_there():
    """
    After the transpiling to the sync version this becomes a regular function.
    """
    pass


def is_async():
    return inspect.iscoroutinefunction(hi_there)


