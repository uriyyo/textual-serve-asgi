from __future__ import annotations

import asyncio
from asyncio.subprocess import Process

from textual_serve.app_service import AppService as BaseAppService


class AppService(BaseAppService):
    def _build_environment(
        self,
        width: int = 80,
        height: int = 24,
        cell_width: int | None = None,
        cell_height: int | None = None,
    ) -> dict[str, str]:
        environment = super()._build_environment(width=width, height=height)

        if cell_width and cell_height:
            environment["TEXTUAL_CELL_WIDTH"] = str(cell_width)
            environment["TEXTUAL_CELL_HEIGHT"] = str(cell_height)

        return environment

    async def _open_app_process(
        self,
        width: int = 80,
        height: int = 24,
        cell_width: int | None = None,
        cell_height: int | None = None,
    ) -> Process:
        environment = self._build_environment(
            width=width,
            height=height,
            cell_width=cell_width,
            cell_height=cell_height,
        )
        self._process = process = await asyncio.create_subprocess_shell(
            self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )
        if process.stdin is None:
            raise RuntimeError("Subprocess stdin was not created")

        self._stdin = process.stdin

        return process

    async def start(
        self,
        width: int,
        height: int,
        cell_width: int | None = None,
        cell_height: int | None = None,
    ) -> None:
        await self._open_app_process(
            width,
            height,
            cell_width=cell_width,
            cell_height=cell_height,
        )
        self._task = asyncio.create_task(self.run())


__all__ = [
    "AppService",
]
