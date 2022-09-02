try:
    import asyncflag
except ImportError:
    IS_ASYNC = False
else:
    IS_ASYNC = True


def is_async():
    return IS_ASYNC


