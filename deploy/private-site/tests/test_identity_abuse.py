"""Original Nginx limiter checks; no IdP, network egress or mail is used.

Run with Python's standard library. Runtime checks need the exact cached image;
they skip when Docker is unavailable and never pull an image.
"""

import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid

CONF = pathlib.Path(__file__).resolve().parents[1] / "identity-nginx.conf"
IMAGE = "nginx:alpine@sha256:df221db836e1754089190208cee7eeda94f233197056426eda74a43ab1abeac2"


class GuardConfiguration(unittest.TestCase):
    def test_closed_proxy_and_no_authentication_url_logs(self):
        config = CONF.read_text(encoding="utf-8")
        self.assertIn("set_real_ip_from __CADDY_TRUSTED_IP__;", config)
        self.assertNotIn("set_real_ip_from 0.0.0.0/0", config)
        self.assertNotIn("set_real_ip_from ::/0", config)
        self.assertIn("real_ip_header X-MayorTech-Client-IP;", config)
        self.assertIn("access_log off;", config)
        self.assertIn("error_log /dev/stderr crit;", config)
        self.assertIn("proxy_pass http://__KEYCLOAK_UPSTREAM__;", config)
        self.assertNotIn("listen 443", config)


class GuardRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("docker"):
            raise unittest.SkipTest("Docker is unavailable; no image was downloaded")
        found = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=15)
        if found.returncode:
            raise unittest.SkipTest("Pinned Nginx image is not cached; no pull attempted")
        cls.folder = tempfile.TemporaryDirectory(prefix="mayortech-guard-qa-")
        config = (
            CONF.read_text(encoding="utf-8")
            .replace("__CADDY_TRUSTED_IP__", "127.0.0.1")
            .replace("__KEYCLOAK_UPSTREAM__", "127.0.0.1:8081")
        )
        # A local synthetic upstream and an untrusted peer exist only in this
        # network-disabled fixture. They cannot reach the real IdP or SMTP.
        backend = """
    server { listen 8081; location / { return 204; } }
    server {
        listen 8082;
        location / {
            proxy_bind 127.0.0.2;
            proxy_set_header X-MayorTech-Client-IP $http_x_mayortech_client_ip;
            proxy_pass http://127.0.0.1:8080;
        }
    }
"""
        head, tail = config.rsplit("\n}", 1)
        path = pathlib.Path(cls.folder.name) / "nginx.conf"
        path.write_text(head + backend + "\n}" + tail, encoding="utf-8")
        path.chmod(0o644)
        cls.container = "mayortech-guard-qa-" + uuid.uuid4().hex[:12]
        command = [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--network",
            "none",
            "--name",
            cls.container,
            "--label",
            "io.kerforge.application=mayortech-guard-qa",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=8m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "101:101",
            "--mount",
            f"type=bind,source={path},target=/etc/nginx/nginx.conf,readonly",
            "--entrypoint",
            "nginx",
            IMAGE,
            "-g",
            "daemon off;",
        ]
        syntax_command = command[:-2] + ["-t"]
        syntax_command.remove("--detach")
        syntax = subprocess.run(syntax_command, capture_output=True, text=True, timeout=20)
        if syntax.returncode:
            cls.folder.cleanup()
            raise RuntimeError("Fixture Nginx syntax check: " + syntax.stderr[-2000:])
        started = subprocess.run(command, capture_output=True, text=True, timeout=25)
        if started.returncode:
            cls.folder.cleanup()
            raise RuntimeError("The isolated Nginx fixture did not start")
        cls.addClassCleanup(cls.tearDownClass)
        for _ in range(30):
            try:
                if cls.request("/resources/fixture.js")[0] == 204:
                    return
            except RuntimeError:
                pass
            time.sleep(0.05)
        cls.tearDownClass()
        raise RuntimeError("The isolated Nginx fixture did not become ready")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "container", None):
            # Only the randomized fixture container is removed, never volumes
            # or images. Docker --rm and TemporaryDirectory own their cleanup.
            subprocess.run(
                ["docker", "rm", "--force", cls.container],
                capture_output=True,
                timeout=15,
            )
            cls.container = None
        if getattr(cls, "folder", None):
            cls.folder.cleanup()

    @classmethod
    def request(cls, path, *, ip="198.51.100.1", post=False, port=8080, head=False):
        command = [
            "docker",
            "exec",
            cls.container,
            "curl",
            "--include",
            "--silent",
            "--show-error",
            "--max-time",
            "5",
            "--path-as-is",
            "--header",
            "X-MayorTech-Client-IP: " + ip,
            "--header",
            "CF-Connecting-IP: " + ip,
            "--header",
            "X-Forwarded-For: " + ip,
        ]
        if head:
            command.append("--head")
        elif post:
            command.extend(["--data", "fixture-only"])
        command.append(f"http://127.0.0.1:{port}{path}")
        response = subprocess.run(command, capture_output=True, text=True, timeout=10)
        match = re.search(r"HTTP/\d(?:\.\d)?\s+(\d{3})", response.stdout)
        if not match:
            raise RuntimeError("Synthetic HTTP response missing: " + response.stderr[:200])
        return int(match.group(1)), response.stdout

    def test_10_untrusted_peer_cannot_spoof_a_new_ip_per_request(self):
        responses = [
            self.request(
                "/realms/mayortech/login-actions/registration",
                ip=f"198.51.100.{index}",
                post=True,
                port=8082,
            )[0]
            for index in range(20, 26)
        ]
        self.assertIn(204, responses)
        self.assertIn(429, responses)

    def test_20_email_burst_and_separate_trusted_clients(self):
        path = "/realms/mayortech/login-actions/registration?login_hint=FAKE&token=FAKE"
        responses = [self.request(path, ip="198.51.100.50", post=True) for _ in range(6)]
        self.assertEqual(responses[0][0], 204)
        limited = [headers for status, headers in responses if status == 429]
        self.assertTrue(limited)
        self.assertRegex(limited[0].lower(), r"retry-after:\s*60")
        self.assertEqual(self.request(path, ip="198.51.100.51", post=True)[0], 204)

    def test_30_distributed_email_requests_have_a_global_budget(self):
        responses = [
            self.request(
                "/realms/mayortech/login-actions/reset-credentials",
                ip=f"203.0.113.{index}",
                post=True,
            )[0]
            for index in range(1, 21)
        ]
        self.assertIn(429, responses)

    def test_40_get_assets_login_and_backchannel_remain_available(self):
        self.assertEqual(self.request("/guard-health")[0], 200)
        self.assertEqual(self.request("/guard-health", port=8082)[0], 404)
        for _ in range(25):
            self.assertEqual(self.request("/resources/fixture.js")[0], 204)
        self.assertEqual(self.request("/realms/mayortech/protocol/openid-connect/auth")[0], 204)
        self.assertEqual(
            self.request("/realms/mayortech/protocol/openid-connect/token", post=True)[0],
            204,
        )
        for path in ("/", "/admin/", "/realms/master/protocol/openid-connect/auth"):
            self.assertEqual(self.request(path)[0], 404)
        logs = subprocess.run(["docker", "logs", self.container], capture_output=True, text=True, timeout=10)
        self.assertNotIn("FAKE", logs.stdout + logs.stderr)
        self.assertNotIn("login_hint", logs.stdout + logs.stderr)

    def test_35_login_post_burst_is_limited_without_an_email_operation(self):
        responses = [
            self.request("/realms/mayortech/login-actions/authenticate", ip="192.0.2.70", post=True)[0]
            for _ in range(30)
        ]
        self.assertIn(204, responses)
        self.assertIn(429, responses)

    def test_50_normalized_paths_and_verify_email_do_not_bypass_budgets(self):
        paths = (
            "/realms/mayortech/login-actions/required-action?execution=VERIFY_EMAIL",
            "/realms/mayortech/login-actions/REGISTRATION",
            "/realms/mayortech//login-actions/registration",
            "/realms/mayortech/login-actions/%72egistration",
            "/realms/mayortech/login-actions/registration/",
            "/realms/mayortech/login-actions/reset-credentials",
        )
        for index, path in enumerate(paths):
            with self.subTest(path=path):
                responses = [self.request(path, ip=f"192.0.2.{100 + index}", post=True)[0] for _ in range(6)]
                self.assertIn(429, responses)
        self.assertEqual(
            self.request("/realms/mayortech/login-actions;ignored/registration", post=True)[0],
            404,
        )

    def test_55_get_required_action_resend_uses_the_email_budget(self):
        responses = [
            self.request(
                "/realms/mayortech/login-actions/required-action?execution=VERIFY_EMAIL",
                ip="192.0.2.180",
            )[0]
            for _ in range(6)
        ]
        self.assertIn(429, responses)
        self.assertEqual(
            self.request(
                "/realms/mayortech/login-actions/required-action?execution=VERIFY_EMAIL",
                ip="192.0.2.180",
                head=True,
            )[0],
            429,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
