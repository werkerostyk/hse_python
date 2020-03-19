import asyncio
import concurrent.futures
import requests
import lxml.html
import pandas as pd

async def scrap_and_parse(urls):
    sub_urls = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        loop = asyncio.get_event_loop()
        futures = [loop.run_in_executor(executor, requests.get, url) for url in urls]
        for response in await asyncio.gather(*futures):
            tree = lxml.html.fromstring(response.text)
            sub_urls.extend(['http://zpp.rospotrebnadzor.ru' + s \
                for s in tree.xpath('//a[@class="appeal-title-link"]/@href')])

    texts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        loop = asyncio.get_event_loop()
        futures = [loop.run_in_executor(executor, requests.get, url) for url in sub_urls]
        for response in await asyncio.gather(*futures):
            tree = lxml.html.fromstring(response.text)
            texts.extend((tree.xpath('//p[@class="appeal-details-message"]/text()')))

    return texts


urls = [f'http://zpp.rospotrebnadzor.ru/Forum/Appeals/AjaxindexList?page={x}&categories=[]' \
        for x in range(1,201)]
loop = asyncio.get_event_loop()
texts = loop.run_until_complete(scrap_and_parse(urls))
df = pd.DataFrame(texts, columns=['label'])
df.to_csv('texts.csv', index=False)
