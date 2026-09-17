# C3XRA — Data Management Plan (DRAFT, design-only)

**No human data exists at the time of writing.** This DMP governs a future genuinely independent C3XRP
replication. Placeholders in `{{ }}` MUST be completed by the responsible institution before acquisition.

## 1. Roles
- Principal Investigator: `{{PI_NAME}}` — Data Controller: `{{INSTITUTION}}` — DPO: `{{DPO_CONTACT}}`.

## 2. Participant coding & pseudonym separation
- Each participant receives a study code `C3XRP-###` at consent. The **key file** linking code ↔ identity
  is held **separately** from all research data, encrypted, accessible only to the PI and one delegate.
- BIDS `participant_id` uses the study code only. No name, DOB, address, or MRN enters any research file,
  filename, JSON sidecar, or Git repository.

## 3. Storage, encryption, access
- Research data at rest on `{{INSTITUTIONAL_ENCRYPTED_STORE}}` (AES-256, full-disk + at-rest).
- Access is role-based, least-privilege, logged. MFA required.
- MRI console → analysis transfer over `{{SECURE_TRANSFER}}` (no email, no consumer cloud).

## 4. Backups & integrity
- 3-2-1 backups; nightly encrypted backup to `{{BACKUP_LOCATION}}`; quarterly restore test.
- File integrity by SHA-256 manifests; BIDS validation on ingest.

## 5. Retention & withdrawal
- Retention: `{{RETENTION_YEARS}}` years per `{{INSTITUTIONAL_POLICY}}`, then secure deletion.
- Withdrawal: a participant may withdraw at any time; already-acquired data are handled per the consent
  form option chosen (destroy vs. retain-anonymized). Withdrawal is a **technical** event and never
  reclassifies other participants.

## 6. MRI data transfer
- DICOM pulled from console to the encrypted store, de-faced (`{{DEFACE_TOOL}}`), converted to BIDS with
  the study code, then the key file is detached. Facial-feature volumes are de-faced before sharing.

## 7. Sharing / OpenNeuro
- Intended sharing: de-identified, de-faced BIDS on OpenNeuro under `{{LICENSE}}`, **only** with explicit
  consent and ethics approval. Stimuli are shared only as permitted by their license
  (`results/c3xra/stimulus_provenance.json`); restricted media are never redistributed.

## 8. GDPR
- Lawful basis: `{{LAWFUL_BASIS}}` (e.g. consent + public-interest research). Data minimization, purpose
  limitation, storage limitation, and data-subject rights (access/rectification/erasure/withdrawal) apply.
- No special-category data beyond what MRI research strictly requires; MRI safety screening data are held
  under the same protections and not published.

## 9. Git / repository hygiene
- **No PII and no raw neural data are ever committed to Git.** Only design artifacts, synthetic mocks, code,
  seals, and hashes live in the repository. CI (`c3xra-acquisition-readiness`) scans for PII/raw-data
  patterns and fails on violation.
