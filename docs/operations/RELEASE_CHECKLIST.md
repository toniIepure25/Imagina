# Release checklist

**Status:** manual until a signed-release workflow exists.

## Preconditions

- [ ] `main` CI green.
- [ ] Working tree clean.
- [ ] Version bumped in `CITATION.cff`, `frontend/package.json`, and `CHANGELOG.md`.
- [ ] Release compose builds and both services become healthy.
- [ ] `docker compose -f docker-compose.release.yml config` passes.
- [ ] `IMAGINA_EXTRAS="[science]"` is present; the release image imports NumPy/sklearn modules.
- [ ] No secrets, `.env`, participant data, or local database in the build context.
- [ ] Dependency audit reviewed; no unresolved critical vulnerability.
- [ ] SBOM generated (CycloneDX or equivalent).
- [ ] Artifacts signed or hashes published.
- [ ] Security contact and disclosure policy current.

## Smoke test

```bash
docker compose -f docker-compose.release.yml up --build -d
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:3000/ | head
docker compose -f docker-compose.release.yml down
```

## Post-release

- [ ] Tag pushed.
- [ ] GitHub release notes published.
- [ ] Zenodo DOI minted (if applicable).
- [ ] `CITATION.cff` updated with the DOI.
- [ ] Rollback image retained.

## What is not yet automated

- Signed container images.
- SBOM attestation.
- Automated accessibility gate.
- Penetration test.
- Multi-tenant auth.

Do not describe the release as "production-grade" until these are addressed for the intended deployment.
