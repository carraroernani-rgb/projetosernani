"""
Adaptador ASGI -> WSGI, usado apenas para hospedar este app FastAPI em
provedores que só servem aplicações WSGI (ex.: PythonAnywhere no plano
gratuito, que não suporta ASGI/uvicorn diretamente).

Não é necessário para rodar localmente (uvicorn) nem no Railway — só é
importado pelo arquivo de configuração WSGI do PythonAnywhere.
"""
from a2wsgi import ASGIMiddleware

from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
