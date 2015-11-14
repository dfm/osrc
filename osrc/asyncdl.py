# -*- coding: utf-8 -*-

__all__ = ["Downloader"]

from functools import partial

from tornado import ioloop
from tornado import httpclient


class Downloader(object):

    def download(self, urls, **kwargs):
        self.urls = urls
        self.errors = []
        self.results = []

        http_client = httpclient.AsyncHTTPClient()
        [http_client.fetch(url, partial(self.handle_request, url), **kwargs)
         for url in urls]
        ioloop.IOLoop.instance().start()

        if len(self.errors):
            for k, (code, error) in self.errors:
                print(k, code, error)
            raise RuntimeError("{0} errors".format(len(self.errors)))

        return dict(self.results)

    def handle_request(self, url, response):
        if response.error:
            self.errors.append((url, (response.code, response.error)))
        else:
            self.results.append((url, response.body))

        if (len(self.results) + len(self.errors)) == len(self.urls):
            ioloop.IOLoop.instance().stop()
