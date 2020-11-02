from .utils import popconvert


class BaseType:
    def __iadd__(self, other):
        [setattr(self, slot, getattr(other, name))
         for slot, name in zip(self.__slots__, other.__slots__)
         if getattr(self, slot) is not None]

    def __repr__(self):
        return repr({slot: getattr(self, slot) for slot in self.__slots__})


class Article(BaseType):
    __slots__ = 'id', 'title', 'url', 'ns'

    def __init__(self, **kwargs):
        self.id = popconvert(kwargs, 'id', int)
        self.title = popconvert(kwargs, 'title')
        self.url = popconvert(kwargs, 'url')
        self.ns = popconvert(kwargs, 'ns', int)
