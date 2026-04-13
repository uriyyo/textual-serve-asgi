import platform
import shlex

import click

WINDOWS = platform.system() == "Windows"


# copied from textual_dev/tools/run.py
def _is_python_path(path: str) -> bool:
    if path.endswith(".py"):
        return True

    try:
        with open(path) as source:  # noqa: PTH123
            first_line = source.readline()
    except OSError:
        return False

    return first_line.startswith("#!") and "py" in first_line


@click.command()
@click.argument("import_name", metavar="FILE or FILE:APP")
@click.option("-h", "--host", type=str, default="localhost", help="Host to serve on")
@click.option("-p", "--port", type=int, default=8000, help="Port of server")
@click.option(
    "-t",
    "--title",
    type=str,
    default="Textual App",
    help="Name of the app being served",
)
@click.option("-u", "--url", type=str, default=None, help="Public URL")
@click.option("--dev", type=bool, default=False, is_flag=True, help="Enable debug mode")
@click.option(
    "-c",
    "--command",
    "command",
    type=bool,
    default=False,
    help="Run as command rather that a file / module.",
    is_flag=True,
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def serve(  # noqa: PLR0913
    import_name: str,
    host: str,
    port: int,
    title: str,
    url: str | None,
    dev: bool,
    extra_args: tuple[str],
    command: bool = False,
) -> None:
    from textual_serve_asgi.server import Server

    import_name, *args = [
        *shlex.split(import_name, posix=not WINDOWS),
        *extra_args,
    ]

    if command:
        run_args = shlex.join(args)
        run_command = f"{import_name} {run_args}"
    elif _is_python_path(import_name):
        run_command = f"python {import_name}"
    else:
        run_args = shlex.join(args)
        run_command = f"{import_name} {run_args}"

    server = Server(run_command, host, port, title=title, public_url=url)
    server.serve(debug=dev)


if __name__ == "__main__":
    serve()
