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
NSENTER = "/usr/bin/nsenter"
API_PROJECT = "aethos-ps"
API_IMAGE = "ghcr.io/venkateshbr/aethos-ps-api"
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


@dataclass(frozen=True)
class ApprovedAPI:
    release: str
    image_id: str
    container_id: str
    network_id: str
    endpoint_id: str


@dataclass(frozen=True)
class Ingress:
    bridge_index: int
    veth_index: int
    veth_name: str
    mac: str


def nft_rules(ingress: Ingress | None = None, *, readback: bool = False) -> list[str]:
    rules = []
    if ingress is not None:
        interface = f'"{_BRIDGE.interface}"'
        iif = interface if readback else str(ingress.bridge_index)
        rules.append(
            f"iif {iif} iifname {interface} ip saddr {ALLOW.source} ip daddr {ALLOW.destination} "
            f"tcp dport {_BIND[1]} ct original ip daddr {ALLOW.destination} "
            f"ct original proto-dst {_BIND[1]} counter accept"
        )
    return [*rules, f"tcp dport {_BIND[1]} counter drop"]


CHAIN = "type filter hook input priority -10; policy accept;"
BRIDGE_CHAIN = "type filter hook input priority -300; policy accept;"


def bridge_rules(ingress: Ingress | None, *, readback: bool = False) -> list[str]:
    if ingress is None:
        return []  # The inet chain denies both families unconditionally.
    if (not valid_index(ingress.bridge_index) or not valid_index(ingress.veth_index)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,15}", ingress.veth_name) is None
            or re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", ingress.mac) is None):
        raise GuardBlocked("invalid ingress port evidence")
    veth = f'"{ingress.veth_name}"'
    iif = veth if readback else str(ingress.veth_index)
    target = f'meta ibrname "{_BRIDGE.interface}" ip daddr {ALLOW.destination} tcp dport {_BIND[1]}'
    # Bridge INPUT sees the physical port; inet INPUT sees only its bridge master.
    return [
        f"iif {iif} iifname {veth} ether saddr {ingress.mac} ip saddr {ALLOW.source} {target} counter accept",
        f"{target} counter drop",
    ]


def tables(ingress: Ingress | None, *, readback: bool = False) -> tuple[tuple[str, str, list[str]], ...]:
    return (
        ("inet", CHAIN, nft_rules(ingress, readback=readback)),
        ("bridge", BRIDGE_CHAIN, bridge_rules(ingress, readback=readback)),
    )


def require_table(ingress: Ingress | None = None) -> None:
    for family, chain, rules in tables(ingress, readback=True):
        observed = run(NFT, "-s", "-nn", "-y", "list", "table", family, TABLE)
        expected = [f"table {family} {TABLE} {{", "chain input {", chain, *rules, "}", "}"]
        if [line.strip() for line in observed.splitlines()] != expected:
            raise GuardBlocked("dedicated nft INPUT policy missing or drifted")


def replace_table(ingress: Ingress | None = None) -> None:
    batch = []
    for family, chain, rules in tables(ingress):
        prefix = f"{family} {TABLE}"
        batch.extend((
            f"add table {prefix}", f"delete table {prefix}", f"add table {prefix}",
            f"add chain {prefix} input {{ {chain} }}",
            *(f"add rule {prefix} input {rule}" for rule in rules),
        ))
    run(NFT, "-f", "-", data="\n".join(batch) + "\n")
    require_table(ingress)


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


def require_approval() -> ApprovedAPI:
    # The directory and file are provisioned by root only after live signoff.
    parent = APPROVAL.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
        raise GuardBlocked("live approval directory is not root-controlled")
    with os.fdopen(os.open(APPROVAL, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW), "rb") as gate:
        status = os.fstat(gate.fileno())
        if not stat.S_ISREG(status.st_mode) or status.st_uid != 0 or stat.S_IMODE(status.st_mode) != 0o600:
            raise GuardBlocked("live approval file must be root-owned 0600")
        expected = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().encode()
        match = re.fullmatch(
            rb"([0-9a-f]{64})\n([0-9a-f]{40})\n(sha256:[0-9a-f]{64})\n"
            rb"([0-9a-f]{64})\n([0-9a-f]{64})\n([0-9a-f]{64})\n",
            gate.read(512),
        )
        if match is None or match[1] != expected:
            raise GuardBlocked("live approval does not match the guard and exact API release contract")
        return ApprovedAPI(*(field.decode("ascii") for field in match.groups()[1:]))


def require_legacy_off() -> None:
    snapshot = run(SYSTEMCTL, "show", LEGACY, "-p", "ActiveState", "-p", "UnitFileState")
    if set(snapshot.splitlines()) != {"ActiveState=inactive", "UnitFileState=disabled"}:
        raise GuardBlocked("legacy listener must be inactive and disabled")


def docker_endpoint(approved: ApprovedAPI) -> tuple[int, str, str]:
    (network,) = json.loads(run(*DOCKER, "network", "inspect", _BRIDGE.name))
    ipam = network["IPAM"]
    options = network["Options"]
    if not (
        network["Id"] == approved.network_id
        and network["Name"] == _BRIDGE.name and network["Driver"] == _BRIDGE.driver
        and network["Scope"] == "local" and network["Internal"] is True
        and network["EnableIPv6"] is False and network.get("EnableIPv4", True) is True
        and ipam["Driver"] == "default"
        and ipam["Config"] == [{"Subnet": _BRIDGE.subnet, "IPRange": _BRIDGE.dynamic_pool, "Gateway": _BIND[0]}]
        and options["com.docker.network.bridge.name"] == _BRIDGE.interface
        and options.get("com.docker.network.bridge.gateway_mode_ipv4", "nat") == _BRIDGE.gateway_mode
        and options.get("com.docker.network.bridge.inhibit_ipv4", "false") == "false"
    ):
        raise GuardBlocked("Docker bridge identity or IPAM mismatch")
    members = network["Containers"]
    if set(members) != {approved.container_id}:
        raise GuardBlocked("unexpected dedicated bridge membership")
    member = members[approved.container_id]
    mac = member["MacAddress"]
    if (member["EndpointID"] != approved.endpoint_id
            or member["IPv4Address"] != f"{ALLOW.source}/29" or member["IPv6Address"] != ""
            or re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", mac) is None):
        raise GuardBlocked("dedicated Docker endpoint mismatch")

    # Filter inspect output at the CLI: never read the container environment.
    (cid, image, reference, project, service, oneoff, state, settings) = [
        json.loads(line) for line in run(
            *DOCKER, "container", "inspect", "--format", API_INSPECT, approved.container_id,
        ).splitlines()
    ]
    endpoint = settings["Networks"][_BRIDGE.name]
    if not (
        cid == approved.container_id and image == approved.image_id
        and reference == f"{API_IMAGE}:{approved.release}"
        and (project, service, oneoff) == (API_PROJECT, "api", "False")
        and state["Status"] == "running" and state["Running"] is True
        and state["Paused"] is False and state["Restarting"] is False
        and valid_index(state["Pid"])
        and endpoint["NetworkID"] == approved.network_id
        and endpoint["EndpointID"] == approved.endpoint_id
        and endpoint["IPAddress"] == ALLOW.source and endpoint["IPPrefixLen"] == 29
        and endpoint["GlobalIPv6Address"] == "" and endpoint["MacAddress"] == mac
        and endpoint["IPAMConfig"]["IPv4Address"] == ALLOW.source
    ):
        raise GuardBlocked("running Compose API release or endpoint not verified")
    return state["Pid"], settings["SandboxKey"], mac


API_INSPECT = "\n".join((
    "{{json .Id}}", "{{json .Image}}", "{{json .Config.Image}}",
    '{{json (index .Config.Labels "com.docker.compose.project")}}',
    '{{json (index .Config.Labels "com.docker.compose.service")}}',
    '{{json (index .Config.Labels "com.docker.compose.oneoff")}}',
    '{"Status":{{json .State.Status}},"Running":{{json .State.Running}},'
    '"Paused":{{json .State.Paused}},"Restarting":{{json .State.Restarting}},"Pid":{{json .State.Pid}}}',
    '{{json .NetworkSettings}}',
))


def valid_index(value: object) -> bool:
    return type(value) is int and 0 < value <= 2**31 - 1


def endpoint_ingress(approved: ApprovedAPI) -> Ingress:
    pid, sandbox, mac = docker_endpoint(approved)
    index = bridge_index()
    if re.fullmatch(r"/(?:var/)?run/docker/netns/[0-9a-f]{12,64}", sandbox) is None:
        raise GuardBlocked("Docker network namespace unavailable")
    with open(sandbox, "rb") as netns:
        # Pin the nsfs object against PID reuse, including while executing ip.
        if not os.path.samestat(os.fstat(netns.fileno()), os.stat(f"/proc/{pid}/ns/net")):
            raise GuardBlocked("API PID is not in the Docker network namespace")
        enter = (NSENTER, f"--net=/proc/{os.getpid()}/fd/{netns.fileno()}", "--", IP, "-j")
        (route,) = json.loads(run(*enter, "-4", "route", "get", _BIND[0]))
        if route["dst"] != _BIND[0] or route["prefsrc"] != ALLOW.source or "gateway" in route:
            raise GuardBlocked("API route must be directly connected from the reserved source")
        dev = route["dev"]
        if re.fullmatch(r"[A-Za-z0-9_-]{1,15}", dev) is None:
            raise GuardBlocked("invalid API link name")
        (peer,) = json.loads(run(*enter, "-d", "address", "show", "dev", dev))
        (host,) = json.loads(run(IP, "-j", "-d", "link", "show", "master", _BRIDGE.interface))
        if not (
            peer["ifname"] == dev and peer["address"] == mac
            and any(a["family"] == "inet" and a["local"] == ALLOW.source and a["prefixlen"] == 29
                    for a in peer["addr_info"])
            and peer["linkinfo"]["info_kind"] == host["linkinfo"]["info_kind"] == "veth"
            and "UP" in peer["flags"] and "UP" in host["flags"]
            and host["master"] == _BRIDGE.interface
            and valid_index(peer["ifindex"]) and valid_index(host["ifindex"])
            and host["ifindex"] == peer["link_index"] and host["link_index"] == peer["ifindex"]
        ):
            raise GuardBlocked("API endpoint does not match the sole dedicated bridge veth")
    return Ingress(index, host["ifindex"], host["ifname"], mac)


def bridge_index() -> int:
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
    if not valid_index(index):
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


def start_check() -> Ingress:
    require_table()
    approved = require_approval()
    require_legacy_off()
    return endpoint_ingress(approved)


def prepare() -> None:
    start_check()
    if sockets():
        raise GuardBlocked("TCP port is not free before listener start")


def activate(pid: str) -> None:
    require_table()
    require_listener(pid)
    ingress = start_check()
    install_compat()
    if start_check() != ingress:
        raise GuardBlocked("API ingress changed during guard activation")
    replace_table(ingress)
    if endpoint_ingress(require_approval()) != ingress:
        raise GuardBlocked("API ingress changed during nft transaction")


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
