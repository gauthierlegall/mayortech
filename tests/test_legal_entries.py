"""Public information routes must remain readable without opening a workspace."""
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings


class InformationPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.collecting_tags = []
        self.h1_count = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "form", "input", "iframe"}:
            self.collecting_tags.append(tag)
        if tag == "h1":
            self.h1_count += 1
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))


def test_public_information_pages_neither_authenticate_nor_collect_account_data(tmp_path):
    settings = Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "legal.sqlite3", tenant_id="legal-private", public_origin="https://testserver", allowed_hosts=("testserver",))
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        baseline = client.get("/api/v1/session").json()
        assert baseline["authenticated"] is False
        for path, title in (("/mentions-legales.html", "Mentions légales"), ("/confidentialite.html", "Confidentialité")):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert response.headers["cache-control"] == "no-store"
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
            assert "set-cookie" not in response.headers
            page = InformationPage()
            page.feed(response.text)
            assert page.h1_count == 1 and title in response.text
            assert not page.collecting_tags
            assert "/connexion.html" in page.links
            assert "mailto:gauthier29n@gmail.com" in page.links
        assert client.get("/api/v1/session").json() == baseline
        assert client.get("/api/v1/projects").status_code == 401
