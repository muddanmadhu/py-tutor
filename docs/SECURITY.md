# Security Model

## What we are defending against

The platform's defining risk is that it **executes code written by strangers**.
Everything else — auth, injection, secrets — is ordinary web-application
security, and is covered below, but the sandbox is the part that could lose the
whole host.

| Asset | Threat | Control |
| --- | --- | --- |
| The host running the API | Learner code escaping the sandbox | Container isolation, dropped capabilities, non-root, read-only rootfs |
| Other learners' data | Cross-tenant reads via the API | Every query is scoped to `user_id`; ownership is re-checked on every read |
| The database | SQL injection | SQLAlchemy parameterisation everywhere; no string-built SQL |
| Credentials | Theft, brute force | scrypt hashing, generic auth errors, short-lived access tokens |
| The host filesystem | Path traversal in a filename | Reject `..`, absolute paths and non-allowlisted extensions before execution |
| Service availability | Fork bombs, infinite loops, memory exhaustion | PID/CPU/memory caps, wall-clock timeouts, per-user rate limits, output caps |
| Secrets | Leaking into logs or source | Environment-only configuration; never logged; production start-up refuses insecure defaults |
| Learner privacy | Prompt content sent to a model | AI is opt-in per deployment; no learner PII is placed in prompts |

## Code execution

See `docs/EXECUTION_ENGINE.md` for the full design. The summary:

* one disposable container per run, never reused
* `--network none`, so there is no egress and no DNS
* `--read-only` root filesystem; the only writable path is a 32 MB tmpfs
* `--cap-drop ALL` and `--security-opt no-new-privileges`
* non-root UID 5000, owning nothing but the workspace
* memory, CPU and PID caps; swap disabled
* a wall-clock guard above the in-container timeout
* output truncation, so a run cannot exhaust API memory
* automatic cleanup, with an explicit `docker rm -f` backstop

### The Docker socket trade-off

In the compose setup, the API mounts `/var/run/docker.sock` to launch sibling
containers. **Access to that socket is equivalent to root on the host.** It is
acceptable for local development and a single-tenant deployment; it is not
acceptable for a hostile multi-tenant one.

The production shape is a separate **runner service**:

```
API  ──HTTP(mTLS)──►  runner service  ──►  containers
                      (own host/pool, no access to the database)
```

The runner service exposes exactly one operation ("run this job"), holds no
credentials for anything else, and can be replaced by gVisor, Firecracker or a
Kubernetes Job backend without the API changing. `app/execution/factory.py` is
the single seam where that swap happens.

### What the sandbox does not promise

* **Timing side channels.** A determined learner can measure the host.
* **Perfect CPU fairness.** `--cpus` is a quota, not a guarantee of latency.
* **Protection against kernel vulnerabilities.** Containers share a kernel. If
  the threat model includes kernel exploits, use a VM-based runtime.

## Authentication and sessions

* Passwords hashed with `hashlib.scrypt` (RFC 7914), 16 MiB of memory per hash,
  a unique 16-byte salt, and a self-describing storage format so parameters can
  be raised and old hashes upgraded transparently on next login.
* `hmac.compare_digest` for the comparison; malformed stored hashes return
  `False` rather than raising, so a corrupt row is indistinguishable from a wrong
  password.
* JWT access tokens (30 minutes) and refresh tokens (14 days), each carrying a
  `type` claim that is verified — an access token cannot be used to refresh, and
  a refresh token cannot be used as a bearer credential.
* `iss` and `exp` are required claims, not optional ones.
* Login returns the same message for an unknown email and a wrong password, so
  the endpoint cannot be used to enumerate accounts.
* Password strength is enforced server-side (length, character mix, a small
  common-password list) — never only in the browser.

### Known gaps, stated plainly

* **No token revocation list.** A stolen access token is valid until it expires.
  Mitigation today is the short TTL; the fix is a Redis denylist keyed on `jti`,
  which the token already carries for this purpose.
* **No MFA.** Appropriate for a learning platform; would be required before
  storing anything sensitive.
* **Refresh tokens are not rotated on use.** Rotation with reuse-detection is the
  next hardening step.

## Injection

| Vector | Control |
| --- | --- |
| SQL | SQLAlchemy Core/ORM only. `tests/test_code_review.py` also asserts that the review engine flags string-built SQL, because learners write it |
| Command | No `shell=True` anywhere; `subprocess` is called with argv lists and a fixed interpreter path |
| Path traversal | `_validate_path` rejects absolute paths, `..`, NUL bytes and unknown extensions; the runner re-validates inside the container |
| Template/XSS | React escapes by default; the only HTML we render is markdown through `react-markdown`, which does not allow raw HTML |
| Deserialisation | JSON only. `pickle` is never used on anything crossing a trust boundary |

## HTTP hardening

Applied by `SecurityHeadersMiddleware`:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'
Strict-Transport-Security: max-age=31536000; includeSubDomains   (production only)
```

CORS is an explicit allowlist from `PYFORGE_CORS_ORIGINS`; a wildcard origin is
rejected at start-up in production.

## Error handling and information disclosure

* Every failure returns the same envelope. Unexpected exceptions become a 500
  with an opaque message and a correlation id; the stack trace goes to the log,
  never to the client.
* `/docs` and `/openapi.json` are served in all environments by default. If your
  deployment should not expose them, gate them in `create_app` — this is a
  deliberate default for a learning platform, not an oversight.

## Configuration and secrets

`Settings._enforce_production_invariants` refuses to start when
`PYFORGE_ENV=production` and any of these hold:

* `PYFORGE_SECRET_KEY` is a known placeholder or shorter than 32 characters
* `PYFORGE_DEBUG` is true
* `PYFORGE_EXECUTOR` is not `docker`
* the database URL is SQLite
* a CORS origin is `*`

Failing to boot is the correct behaviour: a platform that silently runs
unisolated code with a default signing key is worse than one that is down.

Secrets come from the environment or a secrets manager. `.env` is gitignored.
Nothing in the logging path formats a token, password or full request body.

## Rate limiting and abuse

* Sandbox runs: per-user sliding window (`PYFORGE_EXEC_RATE_LIMIT_PER_MINUTE`).
* AI tutor: per-user daily message cap (`PYFORGE_AI_DAILY_MESSAGE_LIMIT`).
* Concurrency: a process-wide semaphore bounds in-flight containers.

The rate limiter is in-process, which is honest but limited: with multiple API
replicas each gets its own window. `docs/DEPLOYMENT.md` describes the Redis-backed
replacement, which is a one-class change.

## Dependency security

* Backend dependencies are pinned by lower bound in `pyproject.toml` and locked
  in CI by the resolver; run `pip-audit` in the pipeline before release.
* The runner image installs exactly one third-party package (pytest) and purges
  the package lists.
* `npm audit` runs in CI via `npm ci`.
* Renovate/Dependabot is the intended mechanism for updates; the CI matrix is the
  gate.

## Reporting a vulnerability

Do not open a public issue. Email the maintainers with the correlation id (if
relevant), reproduction steps and impact. We will acknowledge within two working
days.

## Security checklist for a change

Before merging anything that touches execution, auth or data access:

- [ ] Does it widen what learner code can reach? If yes, is there a test proving the new boundary?
- [ ] Is every new query scoped to the authenticated user?
- [ ] Does any new SQL use parameters rather than string building?
- [ ] Could any new log line contain a secret, token or full request body?
- [ ] Does any new path come from user input, and if so is it resolved and containment-checked?
- [ ] Does the production invariant check still refuse an unsafe configuration?
