"""Envio de e-mail HTML por SMTP sempre que um artigo novo é processado."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
)
from app.models import Article

logger = logging.getLogger("email_notifier")

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family: -apple-system, Arial, sans-serif; background:#f4f5f7; padding:24px; margin:0;">
  <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;">
    <div style="background:#111827;padding:20px 24px;">
      <span style="color:#9CA3AF;font-size:12px;letter-spacing:.05em;text-transform:uppercase;">Radar de Conteúdo — Concorrentes</span>
      <h1 style="color:#ffffff;font-size:20px;margin:6px 0 0;">{title_pt}</h1>
    </div>
    <div style="padding:24px;">
      <p style="margin:0 0 12px;font-size:13px;color:#6B7280;">
        <strong>Concorrente:</strong> {competitor_name} &nbsp;|&nbsp;
        <strong>Fonte:</strong> <a href="{url}" style="color:#2563EB;">{url}</a>
      </p>

      {extras_html}

      <h2 style="font-size:15px;color:#111827;border-bottom:2px solid #F3F4F6;padding-bottom:6px;">{content_heading}</h2>
      <div style="font-size:14px;color:#374151;line-height:1.7;white-space:pre-wrap;">{content_pt}</div>
    </div>
    <div style="padding:16px 24px;background:#F9FAFB;font-size:12px;color:#9CA3AF;">
      Enviado automaticamente pelo Radar de Conteúdo de Concorrentes.
    </div>
  </div>
</body>
</html>
"""


def send_article_email(article: Article) -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "SMTP_USER/SMTP_PASSWORD não configurados — pulando envio de e-mail "
            "para o artigo '%s'.",
            article.title_pt,
        )
        return

    has_ai_content = bool(article.summary_pt or article.checklist_md)
    if has_ai_content:
        extras_html = f"""
      <h2 style="font-size:15px;color:#111827;border-bottom:2px solid #F3F4F6;padding-bottom:6px;">Resumo acionável</h2>
      <p style="font-size:14px;color:#374151;line-height:1.6;">{article.summary_pt or '—'}</p>

      <h2 style="font-size:15px;color:#111827;border-bottom:2px solid #F3F4F6;padding-bottom:6px;">Checklist / To-Do extraído</h2>
      <pre style="white-space:pre-wrap;font-family:inherit;font-size:14px;color:#374151;background:#F9FAFB;padding:12px;border-radius:8px;">{article.checklist_md or '—'}</pre>

      <h2 style="font-size:15px;color:#111827;border-bottom:2px solid #F3F4F6;padding-bottom:6px;">Ferramentas citadas</h2>
      <p style="font-size:14px;color:#374151;">{article.tools_mentioned or 'Nenhuma ferramenta citada.'}</p>
"""
        content_heading = "Artigo traduzido na íntegra"
    else:
        extras_html = ""
        content_heading = "Artigo original (sem tradução automática configurada)"

    html_body = HTML_TEMPLATE.format(
        title_pt=article.title_pt,
        competitor_name=article.competitor_name,
        url=article.url,
        extras_html=extras_html,
        content_heading=content_heading,
        content_pt=article.content_pt,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Radar Concorrentes] Novo post — {article.competitor_name}: {article.title_pt}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

    logger.info("E-mail enviado para %s sobre o artigo '%s'.", EMAIL_TO, article.title_pt)
