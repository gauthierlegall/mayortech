from travaux.exporting import render_summary_html


def test_readable_html_export_formats_markdown_but_never_executes_source_html_or_loads_remote_images():
    summary = {'version':1,'approved_at':'2026-11-14T12:00:00+00:00','snapshot_revision':3,'coverage':'partial','warnings':['Pièce jointe non lue'],'stale':False,'content':'# Chantier fictif\n\n- Accès piéton maintenu\n\n<script>alert(1)</script>\n\n![tracker](https://attacker.invalid/tracker.png)','citations':[{'source_id':'source-fictive','quote':'<img src=x onerror=alert(1)>'}]}
    html = render_summary_html(summary)
    assert '<h1>Chantier fictif</h1>' in html
    assert '<li>Accès piéton maintenu</li>' in html
    assert '<script>' not in html
    assert '<img' not in html
    assert 'Pièce jointe non lue' in html
    assert 'source-fictive' in html
    assert 'max-width: 868px' in html
