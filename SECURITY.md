# Security policy

## Scope and threat model

IMAGINA is designed to run **locally by default**:

- The backend binds to `127.0.0.1` unless `BACKEND_HOST` is changed.
- There is no multi-tenant authentication layer; the application assumes a
  single trusted operator on a trusted machine.
- Neural data and participant data are expected to stay on the local machine.

Deploying the application on a network or the public internet is a **different
security model** and requires, at minimum: TLS termination, authentication and
authorization, per-user data isolation, encrypted storage, audit logging, and a
data-protection review. The project does not yet provide those controls.

## Supported versions

Security fixes are applied to the latest release on `main`. Pre-release and
legacy demo routes are not supported.

## Reporting a vulnerability

Please do **not** open a public issue for a suspected vulnerability.

Use the repository's private vulnerability reporting channel (GitHub Security
Advisories) or contact the maintainers listed in `GOVERNANCE.md` through a
private channel. Include:

- affected version/commit,
- a minimal reproduction,
- impact assessment (data exposure, code execution, denial of service),
- any suggested mitigation.

You will receive an acknowledgement within 7 days. Please allow 90 days before
public disclosure, or less if a fix is released earlier.

## Secrets and data hygiene

- Never commit `.env` files, API keys, tokens, private keys, or credentials.
- Never commit raw or identifiable participant data, consent records, or
  unredacted neural recordings.
- The `.gitignore` excludes common data and model artifacts, but it is not a
  security boundary; check `git status` before committing.
- CI runs secret scanning and dependency audits. A failing scan blocks merge.

## Container guidance

The development Compose stack is for local use only. It publishes ports on the
host and runs without authentication. Do not expose it to an untrusted network.
Release images, when available, are pinned and run as a non-root user; see
`docs/engineering/RELEASE.md` (added with the release workstream).
