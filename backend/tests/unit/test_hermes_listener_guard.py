"""Policy and host-command contract tests; no production host probes or writes."""

import json
import os
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import hermes_listener_guard as host
from scripts.hermes_listener_guard import (
    LISTENER_POLICY,
    BridgeIdentity,
    GuardBlocked,
    InputRule,
    StartupEvidence,
    listener_verdict,
    require_safe_startup,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("interface", "source", "destination", "protocol", "port", "expected"),
    [
        ("br-aethos-nous", "172.31.254.2", "172.31.254.1", "tcp", 8643, "allow"),
        ("br-aethos-nous", "172.31.254.3", "172.31.254.1", "tcp", 8643, "deny"),
        ("docker0", "172.31.254.2", "172.31.254.1", "tcp", 8643, "deny"),
        ("eth0", "192.0.2.10", "172.31.254.1", "tcp", 8643, "deny"),
        ("lo", "127.0.0.1", "127.0.0.1", "tcp", 8643, "deny"),
        ("br-aethos-nous", "172.31.254.2", "192.0.2.1", "tcp", 8643, "deny"),
        ("br-aethos-nous", "2001:db8::2", "2001:db8::1", "tcp", 8643, "deny"),
        ("lo", "::1", "::1", "tcp", 8643, "deny"),
        ("br-aethos-nous", "::ffff:172.31.254.2", "::ffff:172.31.254.1", "tcp", 8643, "deny"),
        ("eth0", "192.0.2.10", "192.0.2.1", "tcp", 443, None),
        ("eth0", "192.0.2.10", "192.0.2.1", "udp", 8643, None),
    ],
)
def test_listener_policy(interface, source, destination, protocol, port, expected):
    assert listener_verdict(interface, source, destination, protocol, port) == expected


@pytest.fixture
def evidence():
    # Independent synthetic input, not populated from LISTENER_POLICY or the host.
    return StartupEvidence(
        bridge=BridgeIdentity(
            name="aethos-ps-hermes-api",
            driver="bridge",
            interface="br-aethos-nous",
            subnet="172.31.254.0/29",
            dynamic_pool="172.31.254.4/30",
            gateway_cidr="172.31.254.1/29",
            internal=True,
            ipv6=False,
            gateway_mode="nat",
        ),
        gateway_owner="br-aethos-nous",
        bind=("172.31.254.1", 8643),
        port_free=True,
        ipv4_rules=(
            InputRule(
                "allow",
                interface="br-aethos-nous",
                source="172.31.254.2",
                destination="172.31.254.1",
            ),
            InputRule("deny"),
            InputRule("allow"),  # Legacy allow comes after the deny.
        ),
        ipv6_rules=(InputRule("deny"), InputRule("allow")),
    )


def test_startup_accepts_only_with_guard_before_legacy_rules(evidence):
    assert LISTENER_POLICY == (evidence.ipv4_rules[:2], evidence.ipv6_rules[:1])
    require_safe_startup(evidence)


def test_startup_blocks_missing_snapshot():
    with pytest.raises(GuardBlocked, match="evidence unavailable"):
        require_safe_startup(None)


@pytest.mark.parametrize(
    "change",
    [
        {"bridge": None},
        {"gateway_owner": None},
        {"gateway_owner": "docker0"},
        {"bind": None},
        {"bind": ("0.0.0.0", 8643)},
        {"bind": ("::", 8643)},
        {"bind": ("172.31.254.1", 8644)},
        {"port_free": None},
        {"port_free": False},
        {"ipv4_rules": None},
        {"ipv6_rules": None},
        {"ipv6_rules": ()},
        {"ipv6_rules": (InputRule("allow"), InputRule("deny"))},
        {"ipv4_rules": (InputRule("allow"), InputRule("deny"))},
    ],
)
def test_startup_blocks_absent_or_unsafe_evidence(evidence, change):
    with pytest.raises(GuardBlocked):
        require_safe_startup(replace(evidence, **change))


@pytest.mark.parametrize(
    "change",
    [
        {"name": "shared"},
        {"driver": "overlay"},
        {"interface": "docker0"},
        {"subnet": "172.31.254.0/28"},
        {"dynamic_pool": "172.31.254.0/29"},
        {"gateway_cidr": "172.31.254.1/28"},
        {"internal": False},
        {"ipv6": True},
        {"gateway_mode": "isolated"},
    ],
)
def test_startup_blocks_bridge_identity_drift(evidence, change):
    actual_bridge = replace(evidence.bridge, **change)
    with pytest.raises(GuardBlocked, match="bridge"):
        require_safe_startup(replace(evidence, bridge=actual_bridge))


@pytest.mark.parametrize(
    "case", ["accept-first", "drop-first", "no-drop", "wide-source", "wide-interface", "wrong-port"]
)
def test_startup_blocks_ipv4_rule_drift(evidence, case):
    allow, deny, legacy = evidence.ipv4_rules
    rules = {
        "accept-first": (legacy, allow, deny),
        "drop-first": (deny, allow),
        "no-drop": (allow,),
        "wide-source": (replace(allow, source=None), deny),
        "wide-interface": (replace(allow, interface=None), deny),
        "wrong-port": (allow, replace(deny, port=8644)),
    }[case]
    with pytest.raises(GuardBlocked, match="IPv4"):
        require_safe_startup(replace(evidence, ipv4_rules=rules))


@pytest.fixture
def host_commands(monkeypatch):
    docker = {
        "Name": "aethos-ps-hermes-api", "Driver": "bridge", "Scope": "local",
        "Internal": True, "EnableIPv6": False,
        "IPAM": {"Driver": "default", "Config": [{
            "Subnet": "172.31.254.0/29", "IPRange": "172.31.254.4/30", "Gateway": "172.31.254.1",
        }]},
        "Options": {"com.docker.network.bridge.name": "br-aethos-nous"},
        "Containers": {"api": {"IPv4Address": "172.31.254.2/29", "IPv6Address": ""}},
    }
    fixtures = {
        (*host.DOCKER, "network", "inspect", "aethos-ps-hermes-api"): [docker],
        (host.IP, "-j", "-d", "link", "show", "dev", "br-aethos-nous"): [
            {"ifindex": 19, "ifname": "br-aethos-nous", "flags": ["UP"], "linkinfo": {"info_kind": "bridge"}},
        ],
        (host.IP, "-j", "-4", "address", "show"): [{"ifname": "br-aethos-nous", "addr_info": [
            {"local": "172.31.254.1", "prefixlen": 29},
        ]}],
        (host.IP, "-j", "-4", "route", "show", "table", "all"): [
            {"dst": "default", "dev": "eth0"}, {"dst": "172.31.254.0/29", "dev": "br-aethos-nous"},
        ],
        (host.SS, "-H", "-ltn", "( sport = :8643 )"): "",
        (host.SS, "-H", "-ltnp", "( sport = :8643 )"):
            'LISTEN 0 128 172.31.254.1:8643 0.0.0.0:* users:(("python",pid=123,fd=4))\n',
        (host.SYSTEMCTL, "show", host.LEGACY, "-p", "ActiveState", "-p", "UnitFileState"):
            "ActiveState=inactive\nUnitFileState=disabled\n",
        (host.NFT, "-s", "-nn", "list", "table", "inet", host.TABLE):
            "table inet aethos_hermes_530 {\n chain input {\n"
            " type filter hook input priority -10; policy accept;\n tcp dport 8643 counter drop\n }\n}\n",
    }

    def output(*args, data=None):
        assert data is None  # fixture must never write host state
        reply = fixtures[args]
        return reply if isinstance(reply, str) else json.dumps(reply)

    monkeypatch.setattr(host, "run", output)
    monkeypatch.setattr(host, "require_approval", lambda: None)
    return fixtures, docker


def test_real_precheck_reads_kernel_and_docker_contract(host_commands):
    host.prepare()
    assert host.bridge_index() == 19


@pytest.mark.parametrize("change", [
    {"EnableIPv6": True}, {"Internal": False}, {"IPAM": None}, {"Options": {}},
    {"Options": {"com.docker.network.bridge.name": "br-aethos-nous",
                 "com.docker.network.bridge.gateway_mode_ipv4": "isolated"}},
    {"Containers": {"worker": {"IPv4Address": "172.31.254.3/29", "IPv6Address": ""}}},
])
def test_precheck_blocks_docker_drift(host_commands, change):
    _, docker = host_commands
    docker.update(change)
    with pytest.raises((GuardBlocked, TypeError, KeyError)):
        host.prepare()


def test_precheck_blocks_overlapping_vpn_route(host_commands):
    fixtures, _ = host_commands
    fixtures[(host.IP, "-j", "-4", "route", "show", "table", "all")].append(
        {"dst": "172.31.0.0/16", "dev": "tun0"},
    )
    with pytest.raises(GuardBlocked, match="overlapping"):
        host.prepare()


def test_precheck_blocks_port_taken(host_commands):
    fixtures, _ = host_commands
    fixtures[(host.SS, "-H", "-ltn", "( sport = :8643 )")] = "LISTEN 0 128 [::]:8643 [::]:*\n"
    with pytest.raises(GuardBlocked, match="not free"):
        host.prepare()


def test_precheck_blocks_legacy_even_when_inactive(host_commands):
    fixtures, _ = host_commands
    fixtures[(host.SYSTEMCTL, "show", host.LEGACY, "-p", "ActiveState", "-p", "UnitFileState")] = (
        "ActiveState=inactive\nUnitFileState=enabled\n"
    )
    with pytest.raises(GuardBlocked, match="inactive and disabled"):
        host.prepare()


def test_postbind_checks_exact_owned_socket_before_opening(host_commands, monkeypatch):
    calls = []
    monkeypatch.setattr(host, "install_compat", lambda: calls.append("install scoped permit"))
    monkeypatch.setattr(host, "replace_table", lambda index: calls.append(index))
    with pytest.raises(GuardBlocked, match="owning process"):
        host.activate("456")
    assert calls == []
    host.activate("123")
    assert calls == ["install scoped permit", 19]


def test_postbind_refuses_bridge_recreation(host_commands, monkeypatch):
    calls = []
    indices = iter((19, 20))
    monkeypatch.setattr(host, "bridge_index", lambda: next(indices))
    monkeypatch.setattr(host, "install_compat", lambda: calls.append("install scoped permit"))
    monkeypatch.setattr(host, "replace_table", lambda index: calls.append(index))
    with pytest.raises(GuardBlocked, match="changed"):
        host.activate("123")
    assert calls == ["install scoped permit"]


def test_rejected_approval_and_malformed_host_evidence_close_on_failure(monkeypatch, capsys):
    attempts = []
    monkeypatch.setattr(host.os, "geteuid", lambda: 0)
    monkeypatch.setattr(host, "close_guard", lambda: attempts.append("close"))
    for error in (GuardBlocked("approval missing"), json.JSONDecodeError("private", "raw output", 0)):
        def fail(error=error):
            raise error

        monkeypatch.setattr(host, "prepare", fail)
        assert host.main(["prepare"]) == 1
    assert attempts == ["close", "close"]
    assert "raw output" not in capsys.readouterr().err


@pytest.mark.skipif(os.geteuid() != 0, reason="approval file must be genuinely root-owned")
def test_approval_file_rejects_missing_stale_loose_mode_and_symlink(tmp_path, monkeypatch):
    path = tmp_path / "host-guard.approved"
    monkeypatch.setattr(host, "APPROVAL", path)
    with pytest.raises(FileNotFoundError):
        host.require_approval()
    path.write_text("stale\n")
    path.chmod(0o600)
    with pytest.raises(GuardBlocked, match="match"):
        host.require_approval()
    path.write_text(sha256(Path(host.__file__).read_bytes()).hexdigest() + "\n")
    host.require_approval()
    path.chmod(0o644)
    with pytest.raises(GuardBlocked, match="0600"):
        host.require_approval()
    target = path.rename(tmp_path / "indirect")
    target.chmod(0o600)
    path.symlink_to(target)
    with pytest.raises(OSError):
        host.require_approval()
