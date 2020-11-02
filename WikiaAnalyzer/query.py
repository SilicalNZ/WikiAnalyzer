from typing import Union, Tuple
from time import time


import aiohttp
import asyncio

from .types import Article
from .parser import PreciseHTMLParser


API_URL = 'https://{wikia}.fandom.com/api/v1/'
RATE_LIMIT = 0.2


class RateLimiter:
    """ONE SUBCLASS PER DOMAIN
       SUBCLASSES ARE SINGLETONS"""

    def __init__(self):
        self.rate_limit_last_call = time()

    def recent_last_call(self) -> bool:
        return self.rate_limit_last_call + RATE_LIMIT < time()

    def update_last_call(self):
        self.rate_limit_last_call = time()

    async def request(self, query):
        if not self.recent_last_call():
            await asyncio.sleep(1)
            return await self.request(query)

        async with aiohttp.ClientSession() as session:
            async with session.get(query) as resp:
                assert resp.status == 200
                self.update_last_call()
                return await resp.json()


class Query:
    def __init__(self, base_string):
        self.base_string = base_string

    def modifiers(self, **kwargs):
        result = self.base_string
        for key, value in kwargs.items():
            result += f'&{key}={value}'
        return Query(result)

    def __repr__(self):
        return repr(self.base_string)

    def __str__(self):
        return str(self.base_string)

    def extend(self, arg):
        result = self.base_string
        result += f'/{arg}'
        return Query(result)


class Queries:
    method_modifier = None

    def __init__(self, wikia_sub):
        self.api_url = Query(API_URL.replace('{wikia}', wikia_sub))
        self._request = RateLimiter().request

    async def query(self, method, modifiers=None):  # Uncached requests
        query = self.api_url.extend(method)
        query.base_string += '?'
        if modifiers:
            query = query.modifiers(**modifiers)
        return await self._request(str(query))

    async def refined_query(self, method, cls, attrs, modifiers=None):
        responses = await self.query(method, modifiers)
        for attr in attrs:
            responses = responses.pop(attr)
        if isinstance(responses, dict):
            return cls(**responses)
        elif isinstance(responses, list):
            result = [cls(**response) for response in responses]
            return result[0] if len(result) == 1 else result
        else:
            return cls(responses)


class SubQueries(Queries):
    def __init__(self, wikia_name):
        self.name = wikia_name
        super().__init__(wikia_name)

    async def fetch_articles(self, **kwargs):
        """category, namespaces, limit, offset, expand"""
        return await self.refined_query('List', ArticleQueries, ('items', ), **kwargs)

    def article(self, title=None, id=None):
        return ArticleQueries(id=id, title=title)

    page = article


class ArticleQueries(Queries, Article):
    def __init__(
        self,
        wikia: Union[str, SubQueries],
        title: str = None,
        id: int = None,
        **kwargs
    ):
        self._HTMLParser = PreciseHTMLParser()

        if isinstance(wikia, SubQueries):
            wikia = wikia.name
        Queries.__init__(self, wikia)
        self.api_url = self.api_url.extend('Articles')
        if id:
            self.id = id
        elif title:
            self.title = title
        else:
            raise ValueError('Missing page identifier')

        Article.__init__(self, id=id, title=title, **kwargs)

    @property
    def _identifier(self):
        if hasattr(self, 'id'):
            return {'id': self.id}
        return {'title': self.title}

    async def content(self):
        return await self.refined_query('AsJson', lambda x: x, ('content', ), self._identifier)

    async def parsed_content(self):
        """The advantage to using this over regular webscraping, is a reduction in redundant information such as ads.
         However, as it is an undocumented request, it is subject to bugs.
         One of which being long waits with changes to the article"""

        return await self.refined_query('AsJson', self._HTMLParser.feed, ('content', ), self._identifier)
