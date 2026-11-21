"""Host-side #530 guard. Invoked only by the dedicated systemd assets."""

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Literal

Verdict = Literal["allow", "deny"]


@dataclass(frozen=True)
class InputRule:
    """Normalized terminal INPUT rule; None means no constraint on that field."""

    verdict: Verdict
    interface: str | None = None
    source: str | None = None
    destination: str | None = None
    protocol: str = "tcp"
    port: int = 8643


@dataclass(frozen=True)
class BridgeIdentity:
    name: str
    driver: str
    interface: str
    subnet: str
    dynamic_pool: str
    gateway_cidr: str
    internal: bool
    ipv6: bool
    gateway_mode: str


@dataclass(frozen=True)
class StartupEvidence:
    """Verified, normalized input only; None means unavailable or ambiguous."""

    bridge: BridgeIdentity | None
    gateway_owner: str | None
    bind: tuple[str, int] | None
    port_free: bool | None
    # Ordered terminal rules effective on this TCP port, per family. Do not
    # omit a rule that could affect the port. Unknown rule paths mean None.
    ipv4_rules: tuple[InputRule, ...] | None
    ipv6_rules: tuple[InputRule, ...] | None


_BRIDGE = BridgeIdentity(
    name="aethos-ps-hermes-api",
    driver="bridge",
    interface="br-aethos-nous",
    subnet="172.31.254.0/29",
    dynamic_pool="172.31.254.4/30",
    gateway_cidr="172.31.254.1/29",
    internal=True,
    ipv6=False,
    gateway_mode="nat",
)
_BIND = ("172.31.254.1", 8643)
LISTENER_POLICY: tuple[tuple[InputRule, ...], tuple[InputRule, ...]] = (
    (InputRule("allow", _BRIDGE.interface, "172.31.254.2", _BIND[0]), InputRule("deny")),
    (InputRule("deny"),),
)


class GuardBlocked(RuntimeError):
    """Startup refused; reasons are static and safe to log."""


def listener_verdict(
    interface: str, source: str, destination: str, protocol: str, port: int
) -> Verdict | None:
    """Evaluate the planned first-match policy; None delegates unrelated traffic."""
    src, dst = ip_address(source), ip_address(destination)
    if src.version != dst.version:
        raise ValueError("source and destination address families must match")
    rules = LISTENER_POLICY[0 if src.version == 4 else 1]
    for rule in rules:
        if (
            rule.port == port
            and rule.protocol == protocol
            and (rule.interface is None or rule.interface == interface)
            and (rule.source is None or rule.source == str(src))
            and (rule.destination is None or rule.destination == str(dst))
        ):
            return rule.verdict
    return None


def require_safe_startup(evidence: StartupEvidence | None) -> None:
    """Raise unless the normalized evidence satisfies the startup prerequisites."""
    if evidence is None:
        raise GuardBlocked("startup evidence unavailable")
    if evidence.bridge != _BRIDGE or evidence.gateway_owner != _BRIDGE.interface:
        raise GuardBlocked("dedicated bridge identity or gateway ownership not verified")
    if evidence.bind != _BIND:
        raise GuardBlocked("listener must use the exact private IPv4 bind")
    if evidence.port_free is not True:
        raise GuardBlocked("listener port is occupied or not verified free")
    for family, observed, required in (
        ("IPv4", evidence.ipv4_rules, LISTENER_POLICY[0]),
        ("IPv6", evidence.ipv6_rules, LISTENER_POLICY[1]),
    ):
        if observed is None or observed[: len(required)] != required:
            raise GuardBlocked(f"{family} listener rule order or scope not verified")


TABLE = "aethos_hermes_530"
TAG = "aethos-hermes-530"
APPROVAL = Path("/etc/aethos-hermes-runtime/host-guard.approved")
NFT = "/usr/sbin/nft"
IP = "/usr/sbin/ip"
IPTABLES = "/usr/sbin/iptables-nft"
SS = "/usr/bin/ss"
SYSTEMCTL = "/usr/bin/systemctl"
DOCKER = ("/usr/bin/docker", "--host=unix:///run/docker.sock")
LEGACY = "aethos-nous-hermes.service"
ALLOW = LISTENER_POLICY[0][0]
COMPAT = (
    "-s", f"{ALLOW.source}/32", "-d", f"{ALLOW.destination}/32", "-i", _BRIDGE.interface,
    "-p", "tcp", "-m", "tcp", "--dport", str(_BIND[1]), "-m", "comment", "--comment", TAG,
    "-j", "ACCEPT",
)


def run(*args: str, data: str | None = None) -> str:
    try:
        result = subprocess.run(
            args, input=data, capture_output=True, text=True, check=True, timeout=6,
            env={"LC_ALL": "C", "HOME": "/", "PATH": "/usr/sbin:/usr/bin"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GuardBlocked(f"{Path(args[0]).name} failed or timed out") from exc
    return result.stdout


def nft_rules(index: int | None = None, *, readback: bool = False) -> list[str]:
    rules = []
    if index is not None:
        if type(index) is not int or index <= 0:
            raise GuardBlocked("invalid bridge ifindex")
        interface = f'"{_BRIDGE.interface}"'
        iif = interface if readback else str(index)
        rules.append(
            f"iif {iif} iifname {interface} ip saddr {ALLOW.source} ip daddr {ALLOW.destination} "
            f"tcp dport {_BIND[1]} ct original ip daddr {ALLOW.destination} "
            f"ct original proto-dst {_BIND[1]} counter accept"
        )
    return [*rules, f"tcp dport {_BIND[1]} counter drop"]


CHAIN = "type filter hook input priority -10; policy accept;"


def require_table(index: int | None = None) -> None:
    observed = run(NFT, "-s", "-nn", "list", "table", "inet", TABLE)
    expected = [
        f"table inet {TABLE} {{", "chain input {", CHAIN,
        *nft_rules(index, readback=True), "}", "}",
    ]
    if [line.strip() for line in observed.splitlines()] != expected:
        raise GuardBlocked("dedicated nft INPUT policy missing or drifted")


def replace_table(index: int | None = None) -> None:
    prefix = f"inet {TABLE}"
    batch = [
        f"add table {prefix}", f"delete table {prefix}", f"add table {prefix}",
        f"add chain {prefix} input {{ {CHAIN} }}",
        *(f"add rule {prefix} input {rule}" for rule in nft_rules(index)),
    ]
    run(NFT, "-f", "-", data="\n".join(batch) + "\n")
    require_table(index)


def compat_rules() -> list[str]:
    return [
        line for line in run(IPTABLES, "-w", "3", "-S", "INPUT").splitlines()
        if line.startswith("-A INPUT ")
    ]


COMPAT_LINE = " ".join(("-A", "INPUT", *COMPAT))


def install_compat() -> None:
    rules = compat_rules()
    tagged = [line for line in rules if TAG in line]
    if tagged and (tagged != [COMPAT_LINE] or rules[0] != COMPAT_LINE):
        raise GuardBlocked("scoped IPv4 INPUT permit duplicated, drifted, or displaced")
    if not tagged:
        run(IPTABLES, "-w", "3", "-I", "INPUT", "1", *COMPAT)
    rules = compat_rules()
    if not rules or rules[0] != COMPAT_LINE or [line for line in rules if TAG in line] != [COMPAT_LINE]:
        raise GuardBlocked("scoped IPv4 INPUT permit not verified first")


def close_guard() -> None:
    # Deny first, then remove only an exact compatibility rule owned by this guard.
    try:
        require_table()
    except GuardBlocked:
        replace_table()
    for line in compat_rules():
        if line == COMPAT_LINE:
            run(IPTABLES, "-w", "3", "-D", "INPUT", *COMPAT)
        elif TAG in line:
            raise GuardBlocked("unexpected tagged IPv4 INPUT rule; deny retained, inspect manually")


def require_approval() -> None:
    # The directory and file are provisioned by root only after live signoff.
    parent = APPROVAL.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
        raise GuardBlocked("live approval directory is not root-controlled")
    with os.fdopen(os.open(APPROVAL, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW), "rb") as gate:
        status = os.fstat(gate.fileno())
        if not stat.S_ISREG(status.st_mode) or status.st_uid != 0 or stat.S_IMODE(status.st_mode) != 0o600:
            raise GuardBlocked("live approval file must be root-owned 0600")
        expected = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().encode() + b"\n"
        if gate.read(len(expected) + 1) != expected:
            raise GuardBlocked("live approval does not match the installed guard")


def require_legacy_off() -> None:
    snapshot = run(SYSTEMCTL, "show", LEGACY, "-p", "ActiveState", "-p", "UnitFileState")
    if set(snapshot.splitlines()) != {"ActiveState=inactive", "UnitFileState=disabled"}:
        raise GuardBlocked("legacy listener must be inactive and disabled")


def docker_bridge() -> None:
    (network,) = json.loads(run(*DOCKER, "network", "inspect", _BRIDGE.name))
    ipam = network["IPAM"]
    options = network["Options"]
    if not (
        network["Name"] == _BRIDGE.name and network["Driver"] == _BRIDGE.driver
        and network["Scope"] == "local" and network["Internal"] is True
        and network["EnableIPv6"] is False and network.get("EnableIPv4", True) is True
        and ipam["Driver"] == "default"
        and ipam["Config"] == [{"Subnet": _BRIDGE.subnet, "IPRange": _BRIDGE.dynamic_pool, "Gateway": _BIND[0]}]
        and options["com.docker.network.bridge.name"] == _BRIDGE.interface
        and options.get("com.docker.network.bridge.gateway_mode_ipv4", "nat") == _BRIDGE.gateway_mode
        and options.get("com.docker.network.bridge.inhibit_ipv4", "false") == "false"
    ):
        raise GuardBlocked("Docker bridge identity or IPAM mismatch")
    members = list(network["Containers"].values())
    if len(members) > 1 or any(
        member["IPv4Address"] != f"{ALLOW.source}/29" or member["IPv6Address"] != ""
        for member in members
    ):
        raise GuardBlocked("unexpected dedicated bridge membership")


def bridge_index() -> int:
    docker_bridge()
    (link,) = json.loads(run(IP, "-j", "-d", "link", "show", "dev", _BRIDGE.interface))
    if link["ifname"] != _BRIDGE.interface or link["linkinfo"]["info_kind"] != "bridge" or "UP" not in link["flags"]:
        raise GuardBlocked("expected Linux bridge is not up")
    subnet = ip_network(_BRIDGE.subnet)
    owners = [
        (device["ifname"], address["local"], address["prefixlen"])
        for device in json.loads(run(IP, "-j", "-4", "address", "show"))
        for address in device["addr_info"]
        if ip_address(address["local"]) in subnet
    ]
    if owners != [(_BRIDGE.interface, _BIND[0], subnet.prefixlen)]:
        raise GuardBlocked("gateway or dedicated subnet ownership mismatch")
    for route in json.loads(run(IP, "-j", "-4", "route", "show", "table", "all")):
        destination = route["dst"]
        if destination in ("default", "0.0.0.0/0"):
            continue
        if ip_network(destination).overlaps(subnet) and route.get("dev") != _BRIDGE.interface:
            raise GuardBlocked("overlapping host route for dedicated subnet")
    index = link["ifindex"]
    if type(index) is not int or index <= 0:
        raise GuardBlocked("Linux bridge ifindex unavailable")
    return index


def sockets(*, processes: bool = False) -> list[str]:
    return run(SS, "-H", "-ltnp" if processes else "-ltn", f"( sport = :{_BIND[1]} )").splitlines()


def require_listener(pid: str) -> None:
    if re.fullmatch(r"[1-9][0-9]*", pid) is None:
        raise GuardBlocked("systemd main PID unavailable")
    deadline = time.monotonic() + 30
    while not (rows := sockets(processes=True)):
        if time.monotonic() >= deadline:
            raise GuardBlocked("listener did not bind before deadline")
        time.sleep(0.25)
    target = f"{_BIND[0]}:{_BIND[1]}"
    pids = re.findall(r"\bpid=(\d+),", rows[0])
    if len(rows) != 1 or rows[0].split()[3] != target or pids != [pid]:
        raise GuardBlocked("listener bind or owning process mismatch")


def start_check() -> int:
    require_table()
    require_approval()
    require_legacy_off()
    return bridge_index()


def prepare() -> None:
    start_check()
    if sockets():
        raise GuardBlocked("TCP port is not free before listener start")


def activate(pid: str) -> None:
    require_table()
    require_listener(pid)
    index = start_check()
    install_compat()
    if bridge_index() != index:
        raise GuardBlocked("bridge changed during guard activation")
    require_table()
    replace_table(index)


def main(args: list[str]) -> int:
    if os.geteuid() != 0 or not (
        args in (["close"], ["prepare"]) or (len(args) == 2 and args[0] == "activate")
    ):
        print("usage (root only): hermes_listener_guard.py close | prepare | activate MAINPID", file=sys.stderr)
        return 2
    try:
        if args[0] == "close":
            close_guard()
        elif args[0] == "prepare":
            prepare()
        else:
            activate(args[1])
    except (GuardBlocked, OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        reason = str(exc) if isinstance(exc, GuardBlocked) else "unavailable or malformed host evidence"
        print(f"Hermes host guard refused {args[0]}: {reason}", file=sys.stderr)
        if args[0] != "close":
            try:
                close_guard()
            except GuardBlocked:
                print("Hermes host guard could not confirm deny cleanup; escalate", file=sys.stderr)
        return 1
    print(f"Hermes host guard: {args[0]} succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
