import re
import typing
import asyncio
import logging
from aiohttp import ClientSession, ClientTimeout, web
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

WORD_RE = re.compile(
    r"""
    (?:[^\W\d_](?:[^\W\d_]|['\-_])+[^\W\d_]) # Words with apostrophes or dashes.
    |
    (?:[+\-]?\d+[,/.:-]\d+[+\-]?)  # Numbers, including fractions, decimals.
    |
    (?:[\w_]+)                     # Words without apostrophes or dashes.
    |
    (?:\.(?:\s*\.){1,})            # Ellipsis dots.
    |
    (?:\S)                         # Everything else that isn't whitespace.
    """,
    re.VERBOSE | re.I | re.UNICODE
)


class Proxy:
    BASE_URL = "https://habr.com"
    SESSION = ClientSession(timeout=ClientTimeout(connect=10, sock_read=60))
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/74.0.3729.169 YaBrowser/19.6.0.1583 Yowser/2.5 Safari/537.36"
    )
    WORD_LENGTH = 6

    def __init__(self, request: web.Request):
        """

        Args:
            request: request to proxy server, proxied url will be build with request.path
        """
        self.request = request

    async def load(self):
        resource = await self.load_resource()
        if isinstance(resource, web.Response):
            return resource
        html = await self.process_html(resource)
        return web.Response(body=html, content_type="text/html", charset="utf-8")

    async def load_resource(self) -> typing.Union[str, web.Response]:
        """
        Load original resource from proxied host.
        """
        try:
            res = await self.SESSION.get(
                f"{self.BASE_URL}{self.request.path}",
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept": "text/html",
                    "Accept-Language": "en,ru;q=0.9,cs;q=0.8,la;q=0.7",
                    "Accept-Encoding": "gzip, deflate",
                },
                verify_ssl=False,
            )
            res.raise_for_status()
        except Exception as e:
            logger.exception("Error while loading page (path=%s, error=%s)", self.request.path, e)
            return web.Response(text=f"<b>Error</b>: {e}", status=500)
        else:
            if res.content_type != "text/html":
                raw = await res.read()
                headers = res.headers.copy()
                headers.pop("Transfer-Encoding", None)
                headers.pop("Content-Encoding", None)
                return web.Response(body=raw, status=res.status, headers=headers)
            html = await res.text(encoding="utf-8")
            return html

    async def process_html(self, html: str) -> str:
        try:
            return await asyncio.get_event_loop().run_in_executor(None, self._process_html, html)
        except Exception as e:
            logger.exception("Error while parsing page, returning original (path=%s, error=%s)", self.request.path, e)
            return html

    def _process_html(self, html: str) -> str:
        soup = BeautifulSoup(markup=html, features="html5lib", from_encoding="utf-8")
        self.replace_links(soup)
        self.replace_words(soup)
        return str(soup)

    def replace_links(self, soup: BeautifulSoup):
        """
        Replace links to proxied host with proxy links.

        Args:
            soup: parsed page instance

        Returns:

        """
        for tag in soup.find_all("a", href=True):
            href = tag.get("href")
            if href and href.startswith(self.BASE_URL):
                tag["href"] = href.replace(self.BASE_URL, "")

        for tag in soup.find_all("use", attrs={"xlink:href": True}):
            href = tag.get("xlink:href")
            if href and href.startswith(self.BASE_URL):
                tag["xlink:href"] = href.replace(self.BASE_URL, "")

    def replace_words(self, soup: BeautifulSoup):
        """
        Find all words of required length and replace them

        Args:
            soup: parsed page instance

        Returns:

        """
        for string in soup.find_all(string=lambda x: x and x.parent.name not in ("script", "style")):
            chars = list(string)
            offset = 0
            for m in WORD_RE.finditer(string):
                start, stop = m.span()
                if start != stop and stop - start == self.WORD_LENGTH:
                    chars.insert(stop + offset, "™")
                    offset += 1

            if offset > 0:
                string.replace_with("".join(chars))
