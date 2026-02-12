from starlette.applications import Starlette

from textual_serve_asgi.server import Server

server = Server("python -m textual")


app = Starlette()
app.mount("/textual", server.asgi_app)
