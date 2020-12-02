# Wikia broke this endpoint during their migration. If you want something similiar, feel free to contact me and request access to a private scraper.

Fandom Wikia (Pythonic API)
========
Feature important queries to the Fandom wikia, translating the responses to python specific terminology. 

Library is built to support the hidden API request `AsJson`. The advantage to using this over regular webscraping, is a reduction in redundant information such as ads. However, as it is an undocumented request, it is subject to bugs. One of which being long waits with changes to the article.

Do not use this library in current state. It is subject to dramatic response changes as I adapt the webscraping capabilities.

## Installing

```
python3 -m pip install -U git+https://github.com/SilicalNZ/WikiaAnalyzer
```

## Requirements
- Python 3.6+
- asyncio
- aiohttp

## Start Process
```
from WikiaAnalyzer import ArticleQueries
import asyncio

async def community_central():
    article = ArticleQueries('community', 'Community_Central')
    print(await article.content())


loop = asyncio.get_event_loop()
loop.run_until_complete(community_central())
```
