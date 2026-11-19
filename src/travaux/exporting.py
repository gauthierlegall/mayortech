"""Readable exports using the pinned La Suite Docs stylesheet and safe Markdown."""
import html
from importlib.resources import files

from markdown_it import MarkdownIt


def render_summary_html(summary):
    parser = MarkdownIt("commonmark", {"html": False, "linkify": False}).disable("image")
    content = parser.render(summary["content"])
    css = files("travaux.vendor").joinpath("docs_export.css").read_text(encoding="utf-8")
    overrides = """
body{font-family:Segoe UI,Arial,sans-serif;line-height:1.6}
main{padding:40px;min-height:0}h1{margin:0 0 24px}h2{margin:28px 0 12px}
p,ul,ol{margin:12px 0}li{margin:6px 0}.export-meta{font-size:14px;color:#48584e}
.coverage-note{padding:12px 16px;background:#fff7e5;color:#68451a;border:1px solid #ceb88c}
.source-quote{white-space:pre-wrap;overflow-wrap:anywhere}small{overflow-wrap:anywhere}
@media(max-width:600px){main{padding:20px 16px}h1{font-size:26px;line-height:1.4}}
@media print{body{background:white}main{padding:0;max-width:none}a{color:inherit}}
"""
    notice = f"Version {summary['version']} · validée le {html.escape(summary['approved_at'] or '')} · mémoire {summary['snapshot_revision']}"
    warnings = list(summary.get("warnings", []))
    if summary.get("stale"):
        warnings.insert(0, "Version archivée : le dossier a évolué depuis cette validation.")
    alert = '<aside class="coverage-note"><strong>Points de vigilance</strong><ul>' + ''.join(f'<li>{html.escape(item)}</li>' for item in warnings) + '</ul></aside>' if warnings else ''
    citations = ''.join(f'<li><blockquote class="source-quote">{html.escape(item["quote"])}</blockquote><small>Source : {html.escape(item["source_id"])}</small></li>' for item in summary["citations"])
    return '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Récapitulatif validé</title><style>' + css + overrides + '</style></head><body><main><header class="export-meta">' + notice + '</header>' + alert + '<article>' + content + '</article><section aria-labelledby="sources-title"><h2 id="sources-title">Sources et preuves</h2><ol>' + citations + '</ol></section></main></body></html>'
