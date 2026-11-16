# CRT data management plan

**Status:** template; no human data exist. This plan must be adapted to the host institution and
GDPR/IRB requirements.

## 1. Data types

| Data | Format | Identifiable? | Storage |
|---|---|---|---|
| Consent records | signed PDF / e-signature | yes | institutional secure store |
| Pseudonymous IDs | CSV | no (key held separately) | local encrypted disk |
| Trial responses | CSV/Parquet | pseudonymous | local encrypted disk |
| Model outputs | JSON | no | repository artifacts |
| Synthetic benchmark | JSON/CSV | no | public repository |
| Session exports | JSON | pseudonymous | participant/lab controlled |

No raw EEG, fMRI, or other neural data are collected in the CRT study.

## 2. Roles

- Controller: institution/PI (to be named).
- Processor: none by default; local-only.
- Data access: PI, named analysts, independent statistician under confidentiality.
- External transfer: prohibited without a DPA and ethics amendment.

## 3. Storage and security

- Encrypted disk; operating-system account protection.
- No participant data in the public repository.
- No participant data in issue trackers, chat, or email attachments.
- Backups encrypted; restore tested.
- Access log for shared lab machines.

## 4. Retention

- Consent: institutional retention period.
- Pseudonymous trial data: pre-specified, e.g. five years after publication, then deletion.
- Analysis code and synthetic data: retained.
- Deletion: documented, with backup expiration.

## 5. Sharing

- Open: code, synthetic benchmark, model specifications, figure scripts.
- Controlled: de-identified summary statistics and analysis code.
- Restricted: participant-level data under a data-use agreement.
- Never: consent records, keys, free-text identifiers.

## 6. Registration and reproducibility

- Freeze code and analysis plan before unblinding.
- Record deviations.
- Publish artifact hashes.
- Independent analyst reproduces the primary result from the frozen package.

## 7. Breach

Follow institutional procedure; assess risk; notify within the legally required window; document
containment and remediation. Do not delete evidence.
