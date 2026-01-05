import asyncio


def Singleton(cls):
    """
    An async-safe singleton decorator for classes.
    Ensures that only one instance of the class is created.
    """
    instances = {}
    lock = asyncio.Lock()

    async def get_instance(*args, **kwargs):
        async with lock:
            if cls not in instances:
                instance = cls(*args, **kwargs)
                # Call async initialize if it exists
                if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
                    await instance.initialize()
                instances[cls] = instance
            return instances[cls]

    cls.instance = staticmethod(get_instance)
    return cls
