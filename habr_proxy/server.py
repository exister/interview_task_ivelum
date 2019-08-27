from aiohttp import web
from proxy import Proxy

routes = web.RouteTableDef()


@routes.get('/{tail:.*}')
async def proxy(request):
    return await Proxy(request).load()


app = web.Application()
app.add_routes(routes)


if __name__ == "__main__":
    web.run_app(app)
