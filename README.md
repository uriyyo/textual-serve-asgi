# textual-serve-asgi

ASGI adapter for [Textual Serve](https://github.com/Textualize/textual-serve) that allows you to serve Textual apps over the web using the ASGI protocol. It can be used to mount Textual apps into FastAPI/Starlette applications.

## Motivation

The original `textual-serve` library provides a way to serve Textual TUI apps over the web, but it runs as a standalone server. There is no built-in way to mount a Textual app as part of an existing web application.

I needed to embed a Textual app into an existing FastAPI/Starlette project as a mounted sub-application — for example, serving a Textual-based admin panel or monitoring dashboard alongside a REST API. This library bridges that gap by providing a standard ASGI interface for Textual Serve, so you can mount it at any path within your app.

It also ships with the latest [xterm.js](https://xtermjs.org/) release, which adds support for in-terminal image rendering — so Textual apps that emit images (via the Kitty/iTerm/Sixel graphics protocols) display them correctly in the browser.

## Installation

```bash
pip install textual-serve-asgi

# include the CLI and uvicorn for standalone serving
pip install "textual-serve-asgi[server]"
```

## Usage

### CLI

Once installed with the `server` extra, a `textual-serve` command is available. It accepts the same style of target as `textual run`:

```bash
# serve a Python file
textual-serve path/to/app.py

# serve a module or an installed console script
textual-serve "python -m textual"

# serve an arbitrary shell command
textual-serve -c "python -m textual"
```

Run `textual-serve --help` for the full list of options.

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
