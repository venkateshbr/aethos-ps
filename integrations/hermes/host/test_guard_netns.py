"""Opt-in real kernel test: python3 -I -B integrations/hermes/host/test_guard_netns.py.

Requires Linux root, nftables/iptables-nft, iproute2 and unshare/nsenter. No
TCP server (or live Docker/systemd) is started. All writes are namespaced.
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def cmd(*argv):
    return subprocess.check_output(argv, text=True, timeout=12)


def peer():
    return subprocess.Popen(["unshare", "-n", "sleep", "120"])


def enter(peer_process, *argv):
    return cmd("nsenter", "-t", str(peer_process.pid), "-n", *argv)


def wait_ns(process):
    for _ in range(100):
        if os.readlink(f"/proc/{process.pid}/ns/net") != os.readlink("/proc/self/ns/net"):
            return
        time.sleep(0.02)
    raise RuntimeError("peer network namespace unavailable")


def connect(namespace, destination, port=8643):
    return enter(
        namespace, sys.executable, "-I", "-B", __file__, "probe", destination, str(port),
    ).strip()


def rules():
    return cmd("iptables-nft", "-S", "INPUT"), cmd("ip6tables-nft", "-S", "INPUT")


def verify(parent_namespace):
    current = os.readlink("/proc/self/ns/net")
    if current in {parent_namespace, os.readlink("/proc/1/ns/net")}:
        raise RuntimeError("refusing to write outside the disposable network namespace")
    source = Path(__file__).resolve().parents[3] / "backend/scripts/hermes_listener_guard.py"
    spec = importlib.util.spec_from_file_location("guard", source)
    guard = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = guard
    spec.loader.exec_module(guard)
    peers = []
    try:
        for _ in range(2):
            process = peer()
            peers.append(process)
            wait_ns(process)
        api, other = peers
        cmd("ip", "link", "add", "br-aethos-nous", "type", "bridge")
        cmd("ip", "addr", "add", "172.31.254.1/29", "dev", "br-aethos-nous")
        cmd("ip", "link", "set", "br-aethos-nous", "up")
        cmd("ip", "link", "add", "api-bridge", "type", "veth", "peer", "name", "api-peer")
        cmd("ip", "link", "set", "api-bridge", "master", "br-aethos-nous")
        cmd("ip", "link", "set", "api-bridge", "up")
        cmd("ip", "link", "set", "api-peer", "netns", str(api.pid))
        enter(api, "ip", "addr", "add", "172.31.254.2/29", "dev", "api-peer")
        enter(api, "ip", "link", "set", "api-peer", "up")
        cmd("ip", "link", "add", "other-host", "type", "veth", "peer", "name", "other-peer")
        cmd("ip", "addr", "add", "192.0.2.1/24", "dev", "other-host")
        cmd("ip", "-6", "addr", "add", "2001:db8::1/64", "dev", "other-host", "nodad")
        cmd("ip", "link", "set", "other-host", "up")
        cmd("ip", "link", "set", "other-peer", "netns", str(other.pid))
        enter(other, "ip", "addr", "add", "192.0.2.2/24", "dev", "other-peer")
        enter(other, "ip", "-6", "addr", "add", "2001:db8::2/64", "dev", "other-peer", "nodad")
        enter(other, "ip", "link", "set", "other-peer", "up")
        cmd("iptables-nft", "-A", "INPUT", "-i", "other-host", "-p", "tcp", "--dport", "8643", "-j", "ACCEPT")
        cmd("iptables-nft", "-A", "INPUT", "-p", "tcp", "--dport", "8643", "-j", "DROP")
        cmd("ip6tables-nft", "-A", "INPUT", "-p", "tcp", "--dport", "8643", "-j", "ACCEPT")
        before = rules()
        guard.close_guard()
        assert connect(api, "172.31.254.1") == "dropped"
        assert connect(other, "192.0.2.1") == "dropped"
        assert connect(other, "2001:db8::1") == "dropped"
        print("PASS closed: intended IPv4, broad legacy IPv4, and legacy IPv6 all denied")

        # Simulate a post-bind transition without actually listening. The exact ss/PID
        # and Docker decisions are tested separately against command-output fixtures.
        index = json.loads(cmd("ip", "-j", "link", "show", "dev", "br-aethos-nous"))[0]["ifindex"]
        port = json.loads(cmd("ip", "-j", "link", "show", "dev", "api-bridge"))[0]
        mac = json.loads(enter(api, "ip", "-j", "link", "show", "dev", "api-peer"))[0]["address"]
        ingress = guard.Ingress(index, port["ifindex"], "api-bridge", mac)
        guard.install_compat()
        guard.install_compat()  # idempotent
        guard.replace_table(ingress)
        assert connect(api, "172.31.254.1") == "refused"
        assert connect(other, "192.0.2.1") == "dropped"
        assert connect(other, "2001:db8::1") == "dropped"
        assert connect(other, "192.0.2.1", 18643) == "refused"
        cmd("iptables-nft", "-t", "nat", "-A", "PREROUTING", "-d", "172.31.254.1", "-p", "tcp", "--dport", "18643", "-j", "REDIRECT", "--to-ports", "8643")
        assert connect(api, "172.31.254.1", 18643) == "dropped"
        guard.require_table(ingress)
        enter(api, "ip", "addr", "del", "172.31.254.2/29", "dev", "api-peer")
        enter(api, "ip", "addr", "add", "172.31.254.3/29", "dev", "api-peer")
        assert connect(api, "172.31.254.1") == "dropped"
        print("PASS open: only exact source/bridge/gateway reaches the socket lookup; DNAT and unrelated port checked")

        # Same bridge, same approved network tuple, different physical port.
        cmd("ip", "link", "delete", "api-bridge")
        cmd("ip", "link", "add", "api-bridge", "type", "veth", "peer", "name", "api-peer")
        cmd("ip", "link", "set", "api-bridge", "master", "br-aethos-nous")
        cmd("ip", "link", "set", "api-bridge", "up")
        cmd("ip", "link", "set", "api-peer", "netns", str(api.pid))
        enter(api, "ip", "link", "set", "api-peer", "address", mac)
        enter(api, "ip", "addr", "add", "172.31.254.2/29", "dev", "api-peer")
        enter(api, "ip", "link", "set", "api-peer", "up")
        assert connect(api, "172.31.254.1") == "dropped"
        assert connect(api, "172.31.254.1", 18644) == "refused"
        print("PASS same-bridge replacement stays denied without a userspace watcher")

        assert guard.main(["prepare"]) == 1  # unexpected open state must close and refuse
        guard.require_table()
        assert rules() == before
        guard.close_guard()  # idempotent boot/stop transition
        guard.require_table()
        assert rules() == before
        cmd("nft", "delete", "table", "inet", guard.TABLE)
        assert guard.main(["prepare"]) == 1  # missing policy must close and refuse
        guard.require_table()
        assert rules() == before
        print("PASS restart refusal and repair on stale or missing policy; legacy INPUT unchanged")
    finally:
        for process in peers:
            process.terminate()
            process.wait(timeout=5)


def probe(destination, port):
    import socket

    try:
        with socket.create_connection((destination, int(port)), timeout=0.7):
            raise AssertionError("no listener may be running in this test")
    except ConnectionRefusedError:
        print("refused")
    except TimeoutError:
        print("dropped")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "probe":
        probe(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "private":
        verify(sys.argv[2])
    elif len(sys.argv) == 1:
        subprocess.run([
            "unshare", "-n", sys.executable, "-I", "-B", __file__, "private",
            os.readlink("/proc/self/ns/net"),
        ], check=True, timeout=70)
    else:
        sys.exit("this test must be run without arguments")
