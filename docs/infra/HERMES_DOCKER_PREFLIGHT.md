# Hostinger: dedicated Hermes Docker preflight (#530)

This stages the API-side path only. Do not apply either Compose file or run the live probe as part of offline validation. Nothing here grants permission to install or restart host services, change firewall rules, cut over chat traffic, or deploy. The existing runtime default, router order, fallback default, and tenant settings are unchanged.

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
  tests/unit/test_hermes_preflight.py tests/unit/test_hermes_client.py)
```

Do not run unfiltered `docker compose config` with live env files. Contract tests check both variants; the probe tests use an ephemeral loopback HTTP fixture and fake credentials, including rejected auth, upstream errors, redirect refusal, and bad output. This is not a Docker data-path, listener, login, provider, or ERP acceptance result.

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
- Sthira owns any host-side cleanup/rollback: keep `8643` denied, stop the dedicated listener before removing its scoped guard or bridge, and do not touch the team gateway. Remove the external bridge only if nothing uses it and a separate approval permits it.
