from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import cached_property
from os import PathLike
from pathlib import Path
from typing import Any, cast

import jinja2
from aiohttp import WSMsgType
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response, StreamingResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocket
from textual_serve.server import Server as BaseServer
from textual_serve.server import to_int

from textual_serve_asgi.app_service import AppService

log = logging.getLogger(__name__)


@dataclass
class WSMsg:
    obj: Any
    type: WSMsgType = WSMsgType.TEXT

    def json(self) -> Any:
        return self.obj


@dataclass
class WSWrapper:
    ws: WebSocket

    async def __aiter__(self) -> AsyncIterator[WSMsg]:
        async for msg in self.ws.iter_json():
            yield WSMsg(msg)

    async def send_json(self, obj: Any) -> None:
        await self.ws.send_json(obj)


class Server(BaseServer):
    def __init__(  # noqa: PLR0913
        self,
        command: str,
        host: str = "localhost",
        port: int = 8000,
        title: str | None = None,
        public_url: str | None = None,
        statics_path: str | PathLike[str] | None = None,
        templates_path: str | PathLike[str] | None = None,
    ) -> None:
        package_root = Path(__file__).resolve().parent
        super().__init__(
            command=command,
            host=host,
            port=port,
            title=title,
            public_url=public_url,
            statics_path=statics_path or package_root / "static",
            templates_path=templates_path or package_root / "templates",
        )

    @cached_property
    def _jinja_env(self) -> jinja2.Environment:
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_path)),
            autoescape=True,
        )

    @cached_property
    def asgi_app(self) -> Starlette:
        return self._make_app()

    @asynccontextmanager
    async def _lifespan(self, app: Starlette) -> AsyncIterator[None]:
        await cast(Any, self).on_startup(app)
        yield
        await cast(Any, self).on_shutdown(app)

    def _make_app(self) -> Starlette:  # ty: ignore[invalid-method-override]
        routes = [
            Route("/", self.handle_index, name="index"),
            WebSocketRoute("/ws", self.handle_websocket, name="websocket"),
            Route("/download/{key:path}", self.handle_download, name="download"),
            Mount("/static", StaticFiles(directory=str(self.statics_path)), name="static"),
        ]

        return Starlette(
            debug=self.debug,
            routes=routes,
            lifespan=self._lifespan,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.asgi_app(scope, receive, send)

    def serve(self, debug: bool = False) -> None:
        try:
            import uvicorn

        except ImportError:
            raise ImportError("Install textual-serve-asgi with server extra to use ASGI server support") from None

        self.debug = debug
        self.initialize_logging()

        uvicorn.run(
            self.asgi_app,
            host=self.host,
            port=self.port,
            log_level="debug" if self.debug else "info",
        )

    def _get_base_url(self, request: Request) -> str:
        base_url = str(request.base_url).rstrip("/")
        if root_path := request.scope.get("root_path", ""):
            base_url += root_path

        return base_url

    def _get_ws_url(self, base_url: str) -> str:
        ws_url = f"{base_url}/ws"
        _, no_scheme = ws_url.split("://", 1)

        if base_url.startswith("https"):
            return f"wss://{no_scheme}"

        return f"ws://{no_scheme}"

    async def handle_index(self, request: Request) -> HTMLResponse:  # ty: ignore[invalid-method-override]
        font_size = to_int(request.query_params.get("fontsize", "16"), 16)

        base_url = self._get_base_url(request)

        context = {
            "font_size": font_size,
            "app_websocket_url": self._get_ws_url(base_url),
            "ping_url": "",
            "config": {
                "static": {
                    "url": f"{base_url}/static/",
                },
            },
            "application": {
                "name": self.title,
            },
        }

        template = self._jinja_env.get_template("app_index.html")
        html = template.render(context)
        return HTMLResponse(html)

    async def handle_download(self, request: Request) -> Response:  # ty: ignore[invalid-method-override]
        key = request.path_params["key"]

        try:
            download_meta = await self.download_manager.get_download_metadata(key)
        except KeyError:
            return Response(f"Download with key {key!r} not found", status_code=404)

        mime_type = download_meta.mime_type
        content_type = mime_type
        if download_meta.encoding:
            content_type += f"; charset={download_meta.encoding}"

        disposition = "inline" if download_meta.open_method == "browser" else "attachment"

        async def stream_body() -> AsyncIterator[bytes]:
            async for chunk in self.download_manager.download(key):
                yield chunk

        content_disposition = f"{disposition}; filename={download_meta.file_name}"

        return StreamingResponse(
            stream_body(),
            media_type=content_type,
            headers={"Content-Disposition": content_disposition},
        )

    async def handle_websocket(self, websocket: WebSocket) -> None:  # ty: ignore[invalid-method-override]
        await websocket.accept()

        width = to_int(websocket.query_params.get("width", "80"), 80)
        height = to_int(websocket.query_params.get("height", "24"), 24)
        cell_width = to_int(websocket.query_params.get("cellWidth", "0"), 0)
        cell_height = to_int(websocket.query_params.get("cellHeight", "0"), 0)

        app_service: AppService | None = None
        try:
            app_service = AppService(
                self.command,
                write_bytes=websocket.send_bytes,
                write_str=websocket.send_text,
                close=websocket.close,
                download_manager=self.download_manager,
                debug=self.debug,
            )
            await app_service.start(
                width,
                height,
                cell_width=cell_width,
                cell_height=cell_height,
            )
            await cast(Any, self)._process_messages(WSWrapper(websocket), app_service)  # noqa: SLF001
        except asyncio.CancelledError:
            await websocket.close()
            raise
        except Exception:
            log.exception("Error in WebSocket connection")
        finally:
            if app_service is not None:
                await app_service.stop()


__all__ = [
    "Server",
]
