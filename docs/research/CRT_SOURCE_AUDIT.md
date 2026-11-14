# CRT source audit — Stage 0I

**Status:** source-integrity audit complete for the records listed below; not a systematic review.
**Artifact:** [`results/crt/CRT_STAGE0I_SOURCE_AUDIT.json`](../../results/crt/CRT_STAGE0I_SOURCE_AUDIT.json)
**Gate:** `ANIMUS_P5_CRT_STAGE0I_SOURCE_INTEGRITY` (PASS for this list only)

This audit records the records actually used in the Stage 0I protocol and theory documents. It does
not estimate a literature-wide effect, establish priority, or claim that every relevant paper was
found. Record status is the status of the cited item, not a quality score.

## Verified records

| ID | Record | Type | DOI / PMID | Used for |
|---|---|---|---|---|
| `cavagnaro_2010` | Cavagnaro et al., adaptive design optimization | peer-reviewed | `10.1162/neco.2009.02-09-959` / PMID 20028226 | mutual-information design utility |
| `myung_2013` | Myung, Cavagnaro & Pitt, ADO tutorial | peer-reviewed | `10.1016/j.jmp.2013.05.005` / PMID 23997275 | design-optimization framing |
| `kim_2014` | Kim et al., hierarchical optimal design | peer-reviewed | `10.1162/neco_a_00654` / PMID 25149697 | hierarchical design optimization |
| `rainforth_2024` | Rainforth et al., modern Bayesian experimental design | peer-reviewed | `10.1214/23-sts915` | Bayesian design framing |
| `adopy_2020` | Yang et al., ADOpy | peer-reviewed | `10.3758/s13428-020-01386-4` | implementation reference |
| `modrak_2025` | Modrák et al., SBC test quantities | peer-reviewed | `10.1214/23-ba1404` / PMID 41049725 | joint-likelihood SBC test quantity |
| `corcoran_2023` | Corcoran et al., Bayesian adversarial collaboration | peer-reviewed | `10.1016/j.neuron.2023.08.027` / PMID 37738981 | adversarial-collaboration **method** |
| `parr_2022` | Parr, Pezzulo & Friston, active inference | book | `10.7551/mitpress/12441.001.0001` | active-inference background only |
| `seyr_2026` | Seyr et al., adversarial-collaboration mapping review | peer-reviewed | `10.3390/publications14030047` | collaboration landscape |
| `dijkstra_fleming_2025_preprint` | Dijkstra & Fleming, perceptual reality monitoring | **preprint** | `10.31234/osf.io/36xdz_v2` | higher-order precision competitor; not peer-reviewed |

## Corrections and exclusions

1. **Corcoran et al. 2023 was mislabelled.** It is “Accelerating scientific progress through
   Bayesian adversarial collaboration,” not an active-inference/source-monitoring empirical result.
   It is now used only as a method reference.
2. **Active-inference background** is attributed to Parr, Pezzulo & Friston (2022), a book, not to
   Corcoran et al.
3. **Dijkstra & Fleming (2025)** is retained as a preprint competitor. It is not used to establish a
   peer-reviewed mechanism or a priority claim.
4. **Tooling limitation:** Crossref returned a Unicode encoding error for `10.1214/23-ba1404`
   (author diacritics); the PubMed/Europe PMC record and DOI landing record were used instead. The
   error is recorded rather than reported as a zero-hit search.

## What this audit does and does not support

It supports a claim that the named records were checked for DOI/PMID metadata, publication type,
and use. It does not support a claim of exhaustive coverage, systematic-review status, novelty,
priority, or a mechanistic conclusion. The Stage 0I text uses “Bayesian adversarial adjudication”
and “identification-first” as descriptions of the planned method, not as results.

## Source-to-claim trail

- ADO design utility → Cavagnaro 2010; Myung 2013; Rainforth 2024.
- Hierarchical design → Kim 2014.
- SBC test-quantity choice → Modrák 2025.
- Adversarial-collaboration method → Corcoran 2023; Seyr 2026.
- Active-inference background → Parr 2022.
- Higher-order precision competitor → Dijkstra & Fleming preprint.
