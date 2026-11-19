"""The public operator can own only the public demo route after the cutover."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import deploy
import remote

ACTIVE_DEMO_SHA256 = 'd385b993639693d0fca104b39bce762d3c781dab8cda30f1cee0588d8cc60d41'


def test_public_address_and_route_are_disjoint_from_protected_and_legacy_guard():
    assert common.DOMAIN == 'demo-travaux.kerforge.com'
    assert common.RUNTIME_DOMAIN == 'travaux.kerforge.com'
    assert common.ROUTE == Path('/opt/caddy/conf.d/travaux-mairie-demo-origin.caddy')
    assert common.ROUTE.name not in {'travaux-mairie.caddy', 'mayortech-travaux-protected.caddy'}


def test_public_renderer_matches_the_already_reviewed_active_alias_exactly():
    rendered = remote.render_route()
    assert hashlib.sha256(rendered.encode()).hexdigest() == ACTIVE_DEMO_SHA256
    assert rendered == common.render_public_demo_route()
    assert rendered.startswith('demo-travaux.kerforge.com {\n')
    assert 'header_up Host travaux.kerforge.com' in rendered
    assert 'request_header -Cookie' in rendered
    assert 'travaux_chat_session={re.mayortechDemoChat.2}' in rendered


def test_public_loopback_probe_retains_the_actual_backend_host_and_origin(monkeypatch):
    commands = []
    monkeypatch.setattr(remote, 'compose', lambda *args, **kwargs: commands.append(args))
    remote.public_auth_probe('fixture-release')
    code = commands[0][-1]
    assert "headers={'Host':'travaux.kerforge.com'}" in code
    assert "'Origin':'https://travaux.kerforge.com'" in code
    assert 'demo-travaux.kerforge.com' not in code


@pytest.mark.parametrize('has_previous', [True, False])
def test_legacy_rollback_cannot_restore_the_protected_hostname_before_any_service_change(tmp_path, monkeypatch, has_previous):
    active = remote.render_route().encode()
    path = tmp_path / 'travaux-mairie-demo-origin.caddy'
    path.write_bytes(active)
    (tmp_path / 'current.json').write_text('{}')
    state = {'release': '20261118T202259Z-39256c', 'route_hash': common.sha256(active),
             'previous': {'release': '20261118T125514Z-369c1f'} if has_previous else None,
             'previous_route': 'travaux.kerforge.com {\n reverse_proxy travaux-mairie-app:8765\n}\n'}
    calls = []
    monkeypatch.setattr(remote, 'BASE', tmp_path)
    monkeypatch.setattr(remote, 'ROUTE', path)
    monkeypatch.setattr(remote, 'current_state', lambda: state)
    monkeypatch.setattr(remote, 'compose', lambda *args, **kwargs: calls.append('compose'))
    monkeypatch.setattr(remote, 'wait_healthy', lambda *args: None)
    monkeypatch.setattr(remote, 'auth_probe', lambda *args: None)
    monkeypatch.setattr(remote, 'restore_route', lambda *args: calls.append('restore'))
    monkeypatch.setattr(remote, 'caddy_id', lambda: 'fixture')
    with pytest.raises(common.DeploymentError, match='legacy_rollback_route_requires_migration'):
        remote.rollback_locked()
    assert calls == []
    assert path.read_bytes() == active


def test_public_route_activation_preserves_protected_and_legacy_guard_bytes(tmp_path):
    protected = tmp_path / 'mayortech-travaux-protected.caddy'
    legacy_guard = tmp_path / 'travaux-mairie.caddy'
    demo = tmp_path / 'travaux-mairie-demo-origin.caddy'
    protected.write_bytes(b'travaux.kerforge.com {\n reverse_proxy private:8765\n}\n')
    legacy_guard.write_bytes(b'# old public deploy must refuse this ownership guard\n')
    before = (protected.read_bytes(), legacy_guard.read_bytes())
    common.activate_route(demo, remote.render_route(), lambda: True, lambda: True)
    assert (protected.read_bytes(), legacy_guard.read_bytes()) == before
    assert common.sha256(demo.read_bytes()) == ACTIVE_DEMO_SHA256


def test_stale_bundle_with_old_operator_is_refused_before_upload_or_ssh(tmp_path, monkeypatch):
    reviewed = {'deploy/hetzner/common.py': 'new-demo-route-contract',
                'deploy/hetzner/remote.py': 'new-demo-only-operator'}
    stale = {'files': {**reviewed, 'deploy/hetzner/common.py': 'old-protected-host-owner'}}
    monkeypatch.setattr(deploy, 'owner_config', lambda *args: {})
    monkeypatch.setattr(common, 'verify_archive', lambda *args: stale)
    monkeypatch.setattr(deploy, 'inventory', lambda *args: reviewed)
    monkeypatch.setattr(deploy, 'upload', lambda *args: pytest.fail('Stale bundle must not reach upload'))
    monkeypatch.setattr(deploy, 'remote_call', lambda *args: pytest.fail('Stale bundle must not reach SSH'))
    monkeypatch.setattr(sys, 'argv', ['deploy.py', 'apply', '--archive', str(tmp_path / 'old.tar.gz')])
    with pytest.raises(common.DeploymentError, match='bundle_differs_from_current_reviewed_source'):
        deploy.main()


def test_legacy_route_guard_refuses_the_old_operator_expected_digest(tmp_path):
    guard = tmp_path / 'travaux-mairie.caddy'
    guard.write_bytes(b'# Protected origin moved; old public operator must refuse this guard.\n')
    before = guard.read_bytes()
    old = b'travaux.kerforge.com {\n reverse_proxy travaux-mairie-app:8765\n}\n'
    with pytest.raises(common.DeploymentError, match='existing_caddy_route_not_owned_or_changed'):
        common.activate_route(guard, old.decode(), lambda: True, lambda: True,
                              expected_previous_hash=common.sha256(old))
    assert guard.read_bytes() == before
