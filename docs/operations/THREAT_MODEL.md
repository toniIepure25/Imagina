# Threat model (local-first lab deployment)

**Status:** initial model. No external security audit has been performed.

## Assets

- Participant behavioural data and pseudonymous IDs.
- Consent records (never in this repository).
- Scene/session databases and exports.
- Model artifacts and code.
- API tokens, if a lab enables them.

## Trust boundaries

1. Browser ↔ local backend (`127.0.0.1` by default).
2. Backend ↔ local SQLite and filesystem.
3. Optional lab LAN ↔ reverse proxy.
4. Operator ↔ container/host.
5. Repository ↔ CI/release pipeline.

## Threats

| Threat | Impact | Current control | Gap |
|---|---|---|---|
| Backend exposed on `0.0.0.0` without auth | data access | default loopback; host validation | no built-in auth |
| Malicious scene input | crash/XSS | typed schema; React escaping | fuzz coverage |
| Path traversal in exports | file read/write | constrained filenames | audit |
| Dependency compromise | code execution | pinned lockfiles; CI | SBOM/signing |
| Secret in image | credential leak | no secrets in repo; `.dockerignore` | secret scanning |
| Participant re-identification | privacy | pseudonymous IDs; local-only | DPA/retention |
| Backup theft | data loss | encrypted disk recommended | encryption not enforced |
| Supply-chain release tampering | malicious image | CI build | image signing |

## Deployment rules

- Bind to loopback unless a reverse proxy with TLS and authentication is in front.
- Do not expose the backend directly to the public internet.
- Use a dedicated OS account and encrypted disk for participant data.
- Keep backups encrypted and test restore.
- Never put participant data in an issue, chat, or public artifact.

## Incident response

1. Stop the service and preserve logs.
2. Assess scope and whether personal data were involved.
3. Follow institutional/GDPR notification.
4. Patch, rotate credentials, and re-test.
5. Document in `SECURITY.md` without disclosing exploit details publicly.
