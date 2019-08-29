from aioresponses import aioresponses
from bs4 import BeautifulSoup

from proxy import Proxy
from server import app


def test_replace_words():
    markup = '<html><head><script>qqqqqq qqqqqq</script></head><body>test <a>qqqqqq qqqqq qqqqqq/qqqqqq "qqqqqq"</a></body></html>'

    soup = BeautifulSoup(markup=markup, features="html5lib", from_encoding="utf-8")
    Proxy(None).replace_words(soup)
    assert str(soup) == '<html><head><script>qqqqqq qqqqqq</script></head><body>test <a>qqqqqq™ qqqqq qqqqqq™/qqqqqq™ "qqqqqq™"</a></body></html>'


def test_replace_links():
    markup = """<html><head><script>qqqqqq qqqqqq</script></head><body>test <a href="https://habr.com/test">qqqqqq qqqqq</a></body></html>"""

    soup = BeautifulSoup(markup=markup, features="html5lib", from_encoding="utf-8")
    Proxy(None).replace_links(soup)
    assert (
        str(soup)
        == """<html><head><script>qqqqqq qqqqqq</script></head><body>test <a href="/test">qqqqqq qqqqq</a></body></html>"""
    )


def test_process_html():
    markup = """<html><head><script>qqqqqq qqqqqq</script></head><body>test <a href="https://habr.com/test">qqqqqq qqqqq</a></body></html>"""

    html = Proxy(None)._process_html(markup)
    assert (
        html
        == """<html><head><script>qqqqqq qqqqqq</script></head><body>test <a href="/test">qqqqqq™ qqqqq</a></body></html>"""
    )


async def test_load(aiohttp_client, loop):
    client = await aiohttp_client(app)

    with aioresponses(passthrough=[f"http://{client.host}:{client.port}"]) as m:
        m.get(
            "https://habr.com/",
            status=200,
            content_type="text/html",
            body="""<html><head><script>qqqqqq qqqqqq</script></head><body>test <a href="https://habr.com/test">qqqqqq qqqqq</a></body></html>""",
        )
        res = await client.get("/")

    assert res.status == 200
    html = await res.text()
    assert (
        html
        == """<html><head><script>qqqqqq qqqqqq</script></head><body>test <a href="/test">qqqqqq™ qqqqq</a></body></html>"""
    )
