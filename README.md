# textual-serve-asgi

ASGI adapter for [Textual Serve](https://github.com/Textualize/textual-serve) that allows you to serve Textual apps over the web using the ASGI protocol. It can be used to mount Textual apps into FastAPI/Starlette applications.

## Motivation

The original `textual-serve` library provides a way to serve Textual TUI apps over the web, but it runs as a standalone server. There is no built-in way to mount a Textual app as part of an existing web application.

I needed to embed a Textual app into an existing FastAPI/Starlette project as a mounted sub-application — for example, serving a Textual-based admin panel or monitoring dashboard alongside a REST API. This library bridges that gap by providing a standard ASGI interface for Textual Serve, so you can mount it at any path within your app.

## Installation

```bash
pip install textual-serve-asgi
```

## Usage

### Standalone

```python
from textual_serve_asgi.server import Server

server = Server("python -m textual")
server.serve()
```

### Mounted in a Starlette/FastAPI app

```python
from starlette.applications import Starlette

from textual_serve_asgi.server import Server

server = Server("python -m textual")

app = Starlette()
app.mount("/textual", server.asgi_app)
```
