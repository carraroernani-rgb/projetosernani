"""
Adaptador ASGI -> WSGI, usado apenas para hospedar este app FastAPI em
provedores que só servem aplicações WSGI (ex.: PythonAnywhere no plano
gratuito, que não suporta ASGI/uvicorn diretamente).

Não usamos a biblioteca a2wsgi aqui: ela cria uma thread de background com
um event loop asyncio próprio (criado uma única vez, na importação do
módulo) para atender todas as requisições. Isso causou travamentos (504)
no PythonAnywhere — o servidor WSGI real (uWSGI) parece não interagir bem
com esse modelo de thread persistente (suspeita: threading do Python não
totalmente habilitado/seguro no worker do uWSGI, ou a thread não
sobrevive/atualiza corretamente entre requisições).

Em vez disso, cada requisição roda seu próprio `asyncio.run()` isolado —
mais simples e sem estado compartilhado entre requisições, ao custo de
recriar o event loop a cada chamada (aceitável para um portal de uso
pessoal/baixo tráfego como este).

Não é necessário para rodar localmente (uvicorn) nem no Railway — só é
usado pelo arquivo de configuração WSGI do PythonAnywhere.
"""
import asyncio
from io import BytesIO
from typing import Any

from app.main import app as asgi_app


def _build_scope(environ: dict) -> dict:
    headers = []
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].lower().replace("_", "-")
            headers.append((name.encode("latin-1"), value.encode("latin-1")))
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH") and value:
            headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "3.0"},
        "http_version": environ.get("SERVER_PROTOCOL", "HTTP/1.1").split("/")[-1],
        "method": environ["REQUEST_METHOD"],
        "scheme": environ.get("wsgi.url_scheme", "http"),
        "path": environ.get("PATH_INFO", ""),
        "raw_path": environ.get("PATH_INFO", "").encode("utf-8"),
        "query_string": environ.get("QUERY_STRING", "").encode("latin-1"),
        "root_path": environ.get("SCRIPT_NAME", ""),
        "server": (environ.get("SERVER_NAME", ""), int(environ.get("SERVER_PORT", 0) or 0)),
        "headers": headers,
        "extensions": {},
    }


async def _run_asgi_request(environ: dict) -> tuple[int, list, bytes]:
    scope = _build_scope(environ)

    body = environ.get("wsgi.input")
    request_body = body.read() if body else b""
    body_sent = False

    async def receive() -> dict:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": request_body, "more_body": False}

    response: dict[str, Any] = {"status": 500, "headers": [], "body": BytesIO()}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response["body"].write(message.get("body", b""))

    await asgi_app(scope, receive, send)
    return response["status"], response["headers"], response["body"].getvalue()


def application(environ: dict, start_response) -> list:
    status_code, headers, body = asyncio.run(_run_asgi_request(environ))

    status_line = f"{status_code} {_status_phrase(status_code)}"
    wsgi_headers = [
        (name.decode("latin-1"), value.decode("latin-1")) for name, value in headers
    ]
    start_response(status_line, wsgi_headers)
    return [body]


_STATUS_PHRASES = {
    200: "OK", 201: "Created", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 303: "See Other", 304: "Not Modified",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
    405: "Method Not Allowed", 422: "Unprocessable Entity",
    500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable",
}


def _status_phrase(code: int) -> str:
    return _STATUS_PHRASES.get(code, "Unknown")
