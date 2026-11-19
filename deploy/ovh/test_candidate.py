"""Validate only synthetic Compose configuration; never contact a Docker daemon."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class OVHCandidateTests(unittest.TestCase):
    def test_required_files_and_proxy_boundary(self):
        for name in ("compose.yaml", "Caddyfile", "healthcheck.py", "README.md"):
            self.assertTrue((HERE / name).is_file(), name)
        proxy = (HERE / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn("{$TRAVAUX_PUBLIC_HOST}", proxy)
        self.assertIn("reverse_proxy 127.0.0.1:8765", proxy)
        site = proxy.split("{$TRAVAUX_PUBLIC_HOST}", 1)[1]
        self.assertNotRegex(site, r"(?m)^\s*log(?:\s|\{|$)")
        self.assertIn("request delete", proxy)
        self.assertIn("resp_headers delete", proxy)
        compile((HERE / "healthcheck.py").read_text(encoding="utf-8"), "healthcheck.py", "exec")

    def test_rendered_private_parameters_and_isolation(self):
        docker = shutil.which("docker")
        if docker is None:
            self.skipTest("Docker CLI absent; Compose rendering not verified")
        with tempfile.TemporaryDirectory(prefix="travaux-ovh-config-") as temporary:
            target = Path(temporary)
            data, key = target / "data", target / "vault.keys"
            data.mkdir()
            key.write_text("EXAMPLE_ONLY_NOT_A_FERNET_KEY\n", encoding="ascii")
            runtime = target / "private.env"
            example = (ROOT / "docs/env/ovh-prive.env.example").read_text(encoding="utf-8")
            marker = "EXAMPLE_ONLY_$NOT_INTERPOLATED#literal"
            runtime.write_text(example.replace("TRAVAUX_OIDC_CLIENT_SECRET=\n", "TRAVAUX_OIDC_CLIENT_SECRET=" + marker + "\n"), encoding="utf-8")
            controls = target / "compose.env"
            controls.write_text("\n".join((
                "TRAVAUX_IMAGE=example.invalid/travaux@sha256:" + "0" * 64,
                "TRAVAUX_PRIVATE_ENV_FILE=" + runtime.as_posix(),
                "TRAVAUX_DATA_DIRECTORY=" + data.as_posix(),
                "TRAVAUX_VAULT_KEY_HOST_FILE=" + key.as_posix(),
            )) + "\n", encoding="utf-8")
            environment = {name: value for name, value in os.environ.items()
                           if not name.startswith(("TRAVAUX_", "COMPOSE_", "DOCKER_"))}
            command = [docker, "compose", "--env-file", str(controls), "-f", str(HERE / "compose.yaml"), "config", "--format", "json"]
            result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            services = json.loads(result.stdout)["services"]
            self.assertEqual(set(services), {"app", "worker"})
            expected = dict(line.split("=", 1) for line in example.splitlines() if line and not line.startswith("#"))
            expected.update(TRAVAUX_DB="/data/travaux.sqlite3", TRAVAUX_AUTH_MODE="oidc",
                            TRAVAUX_CONNECTOR_KEY_FILE="/run/secrets/connector-vault.keys",
                            TRAVAUX_OIDC_CLIENT_SECRET=marker)
            for service in services.values():
                self.assertEqual(service["user"], "10001:10001")
                self.assertTrue(service["read_only"])
                self.assertTrue(service["init"])
                self.assertEqual(service["restart"], "unless-stopped")
                self.assertIn("ALL", service["cap_drop"])
                self.assertTrue(any(value.replace("=", ":") == "no-new-privileges:true" for value in service["security_opt"]))
                self.assertTrue(service["tmpfs"])
                self.assertGreater(int(service["mem_limit"]), 0)
                self.assertGreater(service["pids_limit"], 0)
                self.assertTrue(service["healthcheck"]["test"])
                self.assertNotEqual(service.get("network_mode"), "host")
                for name, value in expected.items():
                    # Compose config re-escapes dollars for its reusable output.
                    self.assertEqual(service["environment"][name], value.replace("$", "$$"), name)
                mounts = {mount["target"]: mount for mount in service["volumes"]}
                self.assertFalse(mounts["/data"].get("read_only", False))
                self.assertTrue(mounts["/run/secrets/connector-vault.keys"]["read_only"])
                self.assertTrue(mounts["/run/travaux/healthcheck.py"]["read_only"])
                self.assertFalse(mounts["/data"]["bind"]["create_host_path"])
                self.assertFalse(mounts["/run/secrets/connector-vault.keys"]["bind"]["create_host_path"])
                self.assertNotIn("docker.sock", str(service["volumes"]))
            ports = services["app"]["ports"]
            self.assertEqual(len(ports), 1)
            self.assertEqual(ports[0]["host_ip"], "127.0.0.1")
            self.assertEqual(str(ports[0]["published"]), "8765")
            self.assertFalse(services["worker"].get("ports"))
            self.assertEqual(services["worker"]["command"], ["python", "-m", "travaux", "worker"])
            self.assertEqual(services["worker"]["depends_on"]["app"]["condition"], "service_healthy")


if __name__ == "__main__":
    unittest.main()
