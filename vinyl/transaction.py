
def atomic():

    if connection.async_connection.get() is not None:
        1