# Hostinger: dedicated Hermes Docker preflight (#530)

This stages the API path and the host guard for review. Do not apply either Compose file or run the live probe as part of offline validation. Nothing here grants permission to install or restart host services, change firewall rules, cut over chat traffic, or deploy. The existing runtime default, router order, fallback default, and tenant settings are unchanged.

## Identity contract for Sthira and Prahari

| Item | Required value |
| --- | --- |
| External Docker network | `aethos-ps-hermes-api`: user-defined Linux bridge, internal, IPv4 only |
| Linux bridge interface | `br-aethos-nous` |
| Subnet / dynamic allocation pool | `172.31.254.0/29` / `172.31.254.4/30` (excludes the API address) |
| Host gateway and listener | `172.31.254.1:8643`; bind only there, not to `docker0`, a wildcard, or the public interface |
| API static address | `172.31.254.2/32` (permit exactly this source, not the subnet) |
| API URL | `http://host.docker.internal:8643`, with an explicit `/etc/hosts` mapping to `172.31.254.1` and a proxy bypass |

`host-gateway` would resolve to the engine-wide gateway, not this dedicated link. The mapping sends traffic over the API's connected route. The normal application bridge stays in place for nginx, DB egress, and the loopback-only `127.0.0.1:8011` API binding. The dedicated bridge must use ordinary internal bridge mode, **not** `gateway_mode_ipv4=isolated` (which removes the host-facing bridge address). The network is external so it can be checked and used for preflight before an application container is attached; Compose does not create, reconcile, or remove it. Missing or incompatible external IPAM must block deployment; never substitute the shared bridge.

Before an approved host change, Sthira must verify the addresses do not overlap with Docker, host, VPC, or VPN ranges, reserve the name and IPAM above, and confirm the bridge settings, lack of other members, exact host bind and effective firewall rule order. The persistent host guard must allow TCP `8643` only on `br-aethos-nous`, from `172.31.254.2` to `172.31.254.1`, then deny other IPv4 and all IPv6 access to that port before any broad legacy allows. Rule and listener activation must fail closed on missing/mismatched identity; review any address change with both sides before use. Repeat the check after Docker/host restarts and API recreation. Do not use live dynamic IPs, the shared subnet, wildcard interfaces, or a second permit for the probe. Restrict Docker daemon access: a privileged Docker operator can take over the reserved address. There is no Docker or Traefik publication of `8643`.

Only `api` receives the Hermes bearer, broker token, and context signing secret. The bearer must match the dedicated listener's `API_SERVER_KEY`/`HERMES_API_SERVER_KEY`; the broker token is separately shared with the dedicated host profile; the signing secret stays API-side. Verify all three are set without rendering or dumping an environment. The Procrastinate worker does **not** require Hermes: the runtime builder is called by the HTTP chat endpoint, while the worker's registered tasks use their own paths (including the in-process `CopilotAgent` for finance-ops). Worker provider credentials are unchanged. Neither worker nor `migrate` gets the dedicated network, hostname mapping, or Hermes secrets. Host-to-ERP tool access remains on the existing broker path; it is not proven by the inference probe.

## Offline validation (no running containers touched)

From the repo root with Docker Compose and Python installed:

```bash
for file in docker-compose.hostinger.yml docker-compose.hostinger.registry.yml; do
  env -i PATH="$PATH" HOME="$HOME" docker compose --env-file /dev/null \
    --profile worker --profile migrate -f "$file" config --quiet || exit 1
done
(cd backend && uv run --offline --group dev pytest --no-cov -q \
  tests/unit/test_hostinger_deployment_contract.py \
  tests/unit/test_hermes_preflight.py tests/unit/test_hermes_client.py \
  tests/unit/test_hermes_listener_guard.py)
```

Do not run unfiltered `docker compose config` with live env files. Contract tests check both variants; the probe tests use an ephemeral loopback HTTP fixture and fake credentials, including rejected auth, upstream errors, redirect refusal, and bad output. This is not a Docker data-path, listener, login, provider, or ERP acceptance result.

### Host guard and startup interlock (PR #593)

The boot unit installs a closed `inet aethos_hermes_530` INPUT table (priority `-10`, before the conventional filter chain). An atomic table-only transaction avoids a rule gap. With the listener stopped, all TCP `8643` is dropped in both families. An `ACCEPT` in the legacy filter chain cannot undo this table's `DROP`. Conversely, a scoped `ACCEPT` here cannot override the legacy IPv4 drop: the helper inserts a single tagged exact permit at the head of iptables-nft INPUT while the nft table is still closed. No other IPv4 or IPv6 rule is modified.

The drop-in requires fresh Docker/IPAM/host/legacy/port evidence and exact closed-table readback before `ExecStart`. While startup is in progress the port remains denied. The unprivileged service retains its sandbox, sets the private IPv4 bind and port, and uses systemd socket-bind restrictions. `ExecStartPost` checks the actual sole TCP listener and systemd main PID, rechecks identity and firewall state, then opens only the bridge ifindex and name, source `.2`, and original and current destination `.1:8643`. Missing/mismatched evidence fails startup; `ExecStopPost` restores the deny and removes only the exact tagged permit. Stopping/restarting the guard or Docker stops the listener through `BindsTo`; the guard unit does not start the listener. An approved restart must pass the same checks. A changed bridge ifindex cannot use a stale permit. No firewall daemon or external writer may flush or replace this table while the service is up; stop and fence the listener before host firewall maintenance. Neither this interlock nor its tests attest to protection against privileged host/Docker administrators or out-of-band ruleset modification.

From the repository root, on an isolated Linux test host with `CAP_SYS_ADMIN` and `CAP_NET_ADMIN`, run `python3 -I -B integrations/hermes/host/test_guard_netns.py`. The suite creates disposable network namespaces and runs the actual nft/iptables code against synthetic legacy rules. No server is started: a reset on the permitted path proves it reached local socket lookup; a timeout on denied paths proves it did not. This does not prove a Docker path, systemd boot, BPF enforcement on the target, Hermes authentication, or app behavior.

### Separately approved host staging and live activation

1. Keep PR #593 draft until reviewers decide otherwise. Before even deny-only installation, have Sthira and Prahari approve the exact head, the reserved CIDR (including Docker/host/VPC/VPN overlap), firewalls and Docker backend, effective units/cgroup v2 socket-bind enforcement, and the rollback. Record the pre-change dedicated unit files, enablement, listeners and INPUT order for both families without recording secrets. Verify neither service nor any proxy publishes port `8643`. Do not touch the team gateway or change application routing.
2. Only in the approved maintenance window, with both Aethos listeners stopped/disabled, stage the root-owned controller at `/opt/aethos-hermes-runtime/hermes_listener_guard.py` (`0644`), the guard unit at `/etc/systemd/system/aethos-hermes-port-guard.service`, and the drop-in at `/etc/systemd/system/aethos-hermes-runtime.service.d/90-host-guard.conf` (both `0644`). Verify the combined effective units with `systemd-analyze verify`, including any local overrides. Reload systemd and enable/start **only** `aethos-hermes-port-guard.service`. Verify the table has only `tcp dport 8643 counter drop` in its INPUT chain, no tagged INPUT permit and no listener. Keep the dedicated listener disabled. An expected failed start (if separately authorized to test the interlock) must stop at `ExecStartPre` without executing Hermes. Never test by slipping in a temporary approval file on the host.
3. Only after recorded live security signoff and explicit owner authorization to start: provision `/etc/aethos-hermes-runtime/host-guard.approved` (`root:root`, `0600`, regular file in the root-controlled directory), containing exactly the lowercase SHA-256 of the installed controller bytes plus one newline. Record the reviewed drop-in/unit hashes with the approval. This file is not a secret or a substitute for signoff. Do not provision it during deny-only staging. Verify the approved bridge identity, reserved API/probe ownership, auth configuration and no proxy or alternate path before starting only `aethos-hermes-runtime.service` (do not enable it by default).
4. Collect exact `ss` bind/PID, nft INPUT/iptables order, allowed and denied path evidence; repeat after separately authorized Docker/host restart and after API recreation. Before moving `.2` from the probe to the API, stop the listener, confirm the closed guard, remove the probe, and repeat the interlocked start only on approved identity. Do not forward traffic or release on successful boot alone.

## Later live gate — only after separate operator approval

After Sthira and Prahari verify the prerequisites and the owner completes private provider login, run the probe on a **disposable** container that temporarily takes `172.31.254.2` before the API claims it. Confirm no endpoint is attached and keep the probe separate from the production Compose project. A trusted, already-local Python image identified by an immutable digest is required. Feed only the dedicated listener bearer through stdin from a protected single-line file outside the worktree (`HERMES_PROBE_KEY_FILE` is the path, not the secret). Do not pass it via argv or environment. Do not use production data, a tenant ID, app secrets, a tool token, published ports, or the team gateway.

```bash
docker run --rm -i --pull=never --log-driver=none \
  --network aethos-ps-hermes-api --ip 172.31.254.2 \
  --add-host host.docker.internal:172.31.254.1 \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --user 65534:65534 --pids-limit=32 \
  --mount "type=bind,src=$PWD/backend/scripts/hermes_preflight.py,dst=/probe.py,readonly" \
  --entrypoint python "$LOCAL_PYTHON_IMAGE" -I -B /probe.py < "$HERMES_PROBE_KEY_FILE"
```

Require exit 0: the same `/v1/responses` endpoint rejected anonymous inference and returned the exact one-time challenge with the bearer. A health check, successful TCP connect, or generic HTTP 200 does not pass. This direct client cannot call Aethos Basic or the semantic router, does not follow redirects or use proxies, requests `store: false`, and prints neither headers nor body. It does not prove the host profile's provider selection or internal fallback policy; correlate the run with dedicated Hermes/provider logs without exposing secrets. Separately have Aksha verify a read-only ERP query using a disposable tenant fixture with correlated Hermes execution evidence and app-level `ATLAS_HERMES_FALLBACK_TO_BASIC=false` **only in that isolated fixture**. No cutover before both gates pass. Confirm the probe container is gone before reserving `.2` for the API.

## Rollback (not performed by this task)

- **Before deploy:** stop at the failed gate and discard the staging changes if needed. The probe uses `--rm` and does not modify the app or the network. Leave the host guard closed; never re-enable shared access as a workaround.
- **If a later approved rollout fails:** restore the recorded last-known-good Compose revision, image SHA and runtime env via the approved release path. For Basic-only recovery set `ATLAS_AI_RUNTIME=aethos_basic` and account for explicit tenant Hermes overrides (they take precedence). Apply the rollback through the API release configuration, not a restart that would retain stale env. Verify `/health/ready` and its build SHA, loopback broker/nginx access and a known-safe Basic turn. No database rollback is required by this change.
- **Review-branch rollback:** revert the host-guard commit on the existing PR branch. No host rollback is needed for offline validation.
- **If a later authorized host guard deployment fails:** halt cutover. Stop and disable only `aethos-hermes-runtime.service` and verify no process is listening on TCP `8643` (IPv4 or IPv6). Remove the approval file. Run the installed controller's `close` action and verify the closed inet INPUT table and absence of the tagged IPv4 permit. Keep the deny-only guard enabled so the closed state survives reboot. Restore only the reviewed dedicated listener drop-in changes from the pre-change record; keep the listener disabled, reload units after approved edits, and verify unaffected rules/services. If close or readback fails, keep the listener off and escalate; do not delete the deny table, flush/restore the shared firewall, reinstate broad permits, start the legacy listener, or touch the team gateway. Remove the bridge only if unused and separately approved. Do not restart until exact bind and both effective firewall paths are reverified under fresh approval.
