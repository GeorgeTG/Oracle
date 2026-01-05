import asyncio
from typing import TypeVar, Type, Any, Protocol, runtime_checkable, ClassVar


@runtime_checkable
class HasInitialize(Protocol):
    """Protocol for classes with an async initialize method."""
    async def initialize(self) -> None: ...


T = TypeVar('T', bound='SingletonMixin')


class SingletonMixin:
    """
    Mixin class for creating async-safe singletons.
    Usage: class MyClass(SingletonMixin): ...
    Access instance: await MyClass.instance()
    """
    _instances: ClassVar[dict[type, Any]] = {}
    _locks: ClassVar[dict[type, asyncio.Lock]] = {}
    
    @classmethod
    async def instance(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """Get or create the singleton instance of this class."""
        if cls not in cls._locks:
            cls._locks[cls] = asyncio.Lock()
        
        async with cls._locks[cls]:
            if cls not in cls._instances:
                instance: T = cls(*args, **kwargs)  # type: ignore[assignment]
                # Call async initialize if it exists
                if isinstance(instance, HasInitialize):
                    await instance.initialize()
                cls._instances[cls] = instance
            return cls._instances[cls]  # type: ignore[return-value]

