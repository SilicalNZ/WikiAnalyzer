from functools import lru_cache
from time import time


import aiohttp
import asyncio

from .types import Article
from .parser import PreciseHTMLParser


API_URL = 'https://{wikia}.fandom.com/api/v1/'
RATE_LIMIT = 0.2
RATE_LIMIT_LAST_CALL = time()


async def request(query):
    global RATE_LIMIT_LAST_CALL
    global RATE_LIMIT


    if RATE_LIMIT_LAST_CALL + RATE_LIMIT > time():
        await asyncio.sleep(RATE_LIMIT)
        return await request(query)

    async with aiohttp.ClientSession() as session:
        async with session.get(query) as resp:
            assert resp.status == 200
            RATE_LIMIT_LAST_CALL = time()
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

    async def query(self, method, modifiers=None):  # Uncached requests
        query = self.api_url.extend(method)
        query.base_string += '?'
        if modifiers:
            query = query.modifiers(**modifiers)
        return await request(str(query))

    async def refined_query(self, method, cls, attrs, modifiers=None):
        responses = await self.query(method, modifiers)
        for attr in attrs:
            responses = responses.pop(attr)
        if isinstance(responses, dict):
            return cls(**responses)
        elif isinstance(responses, list):
            result =  [cls(**response) for response in responses]
            return result[0] if len(result) == 1 else result
        else:
            return cls(responses)

class SubQueries(Queries):
    def __init__(self, wikia_name):
        name = wikia_name
        super().__init__(sub_wikia)

    async def fetch_articles(self, **kwargs):
        """category, namespaces, limit, offset, expand"""
        return await self.refined_query('List', Article, ('items', ), **kwargs)

    def article(self, title=None, id=None):
        return ArticleQueries(id=id, title=title)

    page = article


class ArticleQueries(Queries):
    def __init__(self, wikia, title=None, id=None):
        self._HTMLParser = PreciseHTMLParser()

        if isinstance(wikia, SubQueries):
            wikia = wikia.name
        super().__init__(wikia)
        self.api_url = self.api_url.extend('Articles')
        if id:
            self.id = id
        elif title:
            self.title = title
        else:
            raise ValueError('Missing page identifier')

    @property
    def _identifier(self):
        if hasattr(self, 'id'):
            return {'id': self.id}
        return {'title': self.title}

    async def content(self):
        """The advantage to using this over regular webscraping, is a reduction in redundant information such as ads.
         However, as it is an undocumented request, it is suspect to bugs.
         One of which being long waits with changes to the article"""

        return await self.refined_query('AsJson', self._HTMLParser.feed, ('content', ), self._identifier)
