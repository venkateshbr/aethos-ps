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
APPROVED = host.ApprovedAPI("1" * 40, "sha256:" + "2" * 64, "3" * 64, "4" * 64, "5" * 64)
MAC = "02:01:02:03:04:05"
INGRESS = host.Ingress(19, 21, "vethapproved", MAC)
SANDBOX = "/run/docker/netns/123456abcdef"
INSPECT = (*host.DOCKER, "container", "inspect", "--format", host.API_INSPECT, APPROVED.container_id)


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
        "Id": APPROVED.network_id,
        "Name": "aethos-ps-hermes-api", "Driver": "bridge", "Scope": "local",
        "Internal": True, "EnableIPv6": False,
        "IPAM": {"Driver": "default", "Config": [{
            "Subnet": "172.31.254.0/29", "IPRange": "172.31.254.4/30", "Gateway": "172.31.254.1",
        }]},
        "Options": {"com.docker.network.bridge.name": "br-aethos-nous"},
        "Containers": {APPROVED.container_id: {
            "IPv4Address": "172.31.254.2/29", "IPv6Address": "", "MacAddress": MAC,
            "EndpointID": APPROVED.endpoint_id,
        }},
    }
    fixtures = {
        INSPECT: [
            APPROVED.container_id, APPROVED.image_id, f"{host.API_IMAGE}:{APPROVED.release}",
            "aethos-ps", "api", "False", {"Status": "running", "Running": True, "Paused": False,
                                          "Restarting": False, "Pid": os.getpid()},
            {"SandboxKey": SANDBOX, "Networks": {"aethos-ps-hermes-api": {
                "NetworkID": APPROVED.network_id, "EndpointID": APPROVED.endpoint_id, "MacAddress": MAC,
                "IPAddress": "172.31.254.2", "IPPrefixLen": 29, "GlobalIPv6Address": "",
                "IPAMConfig": {"IPv4Address": "172.31.254.2"},
            }}},
        ],
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
        (host.IP, "-j", "-d", "link", "show", "master", "br-aethos-nous"): [{
            "ifindex": 21, "link_index": 9, "ifname": "vethapproved", "master": "br-aethos-nous",
            "flags": ["UP"], "linkinfo": {"info_kind": "veth"},
        }],
        ("-4", "route", "get", "172.31.254.1"): [{"dst": "172.31.254.1", "prefsrc": "172.31.254.2", "dev": "eth1"}],
        ("-d", "address", "show", "dev", "eth1"): [{
            "ifname": "eth1", "address": MAC, "flags": ["UP"], "ifindex": 9, "link_index": 21,
            "linkinfo": {"info_kind": "veth"},
            "addr_info": [{"family": "inet", "local": "172.31.254.2", "prefixlen": 29}],
        }],
        (host.NFT, "-s", "-nn", "-y", "list", "table", "inet", host.TABLE):
            "table inet aethos_hermes_530 {\n chain input {\n"
            " type filter hook input priority -10; policy accept;\n tcp dport 8643 counter drop\n }\n}\n",
        (host.NFT, "-s", "-nn", "-y", "list", "table", "bridge", host.TABLE):
            "table bridge aethos_hermes_530 {\n chain input {\n"
            " type filter hook input priority -300; policy accept;\n }\n}\n",
    }

    def output(*args, data=None):
        assert data is None  # fixture must never write host state
        if args == INSPECT:
            return "\n".join(map(json.dumps, fixtures[args]))
        if args[0] == host.NSENTER:
            assert args[1].startswith(f"--net=/proc/{os.getpid()}/fd/")
            args = args[5:]
        reply = fixtures[args]
        return reply if isinstance(reply, str) else json.dumps(reply)

    monkeypatch.setattr(host, "run", output)
    monkeypatch.setattr(host, "require_approval", lambda: APPROVED)
    monkeypatch.setattr(host, "open", lambda path, mode: open("/proc/self/ns/net", mode) if path == SANDBOX else None,
                        raising=False)
    return fixtures, docker


def test_real_precheck_reads_kernel_and_docker_contract(host_commands):
    host.prepare()
    assert host.start_check() == INGRESS


@pytest.mark.parametrize("change", [
    {"EnableIPv6": True}, {"Internal": False}, {"IPAM": None}, {"Options": {}},
    {"Options": {"com.docker.network.bridge.name": "br-aethos-nous",
                 "com.docker.network.bridge.gateway_mode_ipv4": "isolated"}},
    {"Containers": {"worker": {"IPv4Address": "172.31.254.3/29", "IPv6Address": ""}}},
    {"Containers": {}},
    {"Containers": {"worker": {"IPv4Address": "172.31.254.2/29", "IPv6Address": ""}}},
    {"Id": "6" * 64},
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


@pytest.mark.parametrize("field,value", [
    (0, "6" * 64), (1, "sha256:" + "6" * 64), (2, f"{host.API_IMAGE}:latest"),
    (3, "other-project"), (4, "worker"), (5, "True"),
    ("Status", "exited"), ("Running", False), ("Paused", True), ("Restarting", True), ("Pid", 0),
    ("EndpointID", "6" * 64), ("NetworkID", "6" * 64), ("IPAMConfig", {}),
    ("MacAddress", "02:00:00:00:00:05"), ("IPAddress", "172.31.254.3"),
    ("GlobalIPv6Address", "2001:db8::1"),
])
def test_precheck_refuses_unapproved_container_or_endpoint(host_commands, field, value):
    fixtures, _ = host_commands
    api = fixtures[INSPECT]
    if isinstance(field, int):
        api[field] = value
    else:
        target = api[6] if field in api[6] else api[7]["Networks"]["aethos-ps-hermes-api"]
        target[field] = value
    with pytest.raises((GuardBlocked, KeyError)):
        host.prepare()


def test_precheck_refuses_extra_member_or_changed_endpoint_id(host_commands):
    _, network = host_commands
    members = network["Containers"]
    members["6" * 64] = members[APPROVED.container_id].copy()
    with pytest.raises(GuardBlocked, match="membership"):
        host.prepare()
    del members["6" * 64]
    members[APPROVED.container_id]["EndpointID"] = "7" * 64
    with pytest.raises(GuardBlocked, match="endpoint mismatch"):
        host.prepare()


@pytest.mark.parametrize(("command", "change"), [
    (("-4", "route", "get", "172.31.254.1"), {"gateway": "172.31.254.6"}),
    (("-4", "route", "get", "172.31.254.1"), {"prefsrc": "172.31.254.4"}),
    (("-d", "address", "show", "dev", "eth1"), {"link_index": 42}),
    (("-d", "address", "show", "dev", "eth1"), {"addr_info": []}),
])
def test_precheck_refuses_wrong_kernel_peer_or_route(host_commands, command, change):
    fixtures, _ = host_commands
    fixtures[command][0].update(change)
    with pytest.raises(GuardBlocked):
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
    assert calls == ["install scoped permit", INGRESS]


@pytest.mark.parametrize("ingress_change", [{"bridge_index": 20}, {"veth_index": 22}])
def test_postbind_refuses_bridge_or_veth_recreation(host_commands, monkeypatch, ingress_change):
    calls = []
    ingress = iter((INGRESS, replace(INGRESS, **ingress_change)))
    monkeypatch.setattr(host, "endpoint_ingress", lambda _: next(ingress))
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


def test_identity_change_during_nft_transaction_recloses(host_commands, monkeypatch):
    calls = []
    ingress = iter((INGRESS, INGRESS, replace(INGRESS, veth_index=22)))
    monkeypatch.setattr(host, "endpoint_ingress", lambda _: next(ingress))
    monkeypatch.setattr(host, "install_compat", lambda: calls.append("compat"))
    monkeypatch.setattr(host, "replace_table", lambda entry: calls.append(entry))
    monkeypatch.setattr(host, "close_guard", lambda: calls.append("close"))
    monkeypatch.setattr(host.os, "geteuid", lambda: 0)
    assert host.main(["activate", "123"]) == 1
    assert calls == ["compat", INGRESS, "close"]


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
    controller = sha256(Path(host.__file__).read_bytes()).hexdigest()
    path.write_text(controller + "\n")
    with pytest.raises(GuardBlocked, match="release contract"):
        host.require_approval()
    path.write_text("\n".join((controller, APPROVED.release, APPROVED.image_id, APPROVED.container_id,
                               APPROVED.network_id, APPROVED.endpoint_id, "")))
    assert host.require_approval() == APPROVED
    path.chmod(0o644)
    with pytest.raises(GuardBlocked, match="0600"):
        host.require_approval()
    target = path.rename(tmp_path / "indirect")
    target.chmod(0o600)
    path.symlink_to(target)
    with pytest.raises(OSError):
        host.require_approval()
