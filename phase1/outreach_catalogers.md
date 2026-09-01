# Cataloger Panel — Outreach & Protocol (RQ5 / ground-truth validation)

## Goal
Recruit 2–3 professional catalogers (or advanced cataloging students under
supervision) for two activities:

1. **Ground-truth validation** (~1.5 h): spot-check a stratified sample (~60 of
   600) of LIBRA-CAT records — confirm LCSH headings and DDC numbers are
   acceptable professional assignments, and flag errors (wrong heading,
   invented heading, wrong class).
2. **Human-in-the-loop study** (RQ5, ~2 h): counterbalanced review of N≈40
   records: catalog manually vs. verify LLM drafts. Measures: time/record,
   edits/record, final quality vs. gold.

## Outreach email (template)

> Subject: Invitation — expert review panel for a study on AI and cataloging
>
> Dear [Name],
>
> We are building LIBRA-Eval, an open benchmark for AI-assisted cataloging and
> library discovery (to be presented at AIDL 2026). The benchmark's ground
> truth must be validated by professional catalogers, and we would like to
> invite you to join a small paid expert panel:
>
> - Activity 1: validate ~60 catalog records (LCSH/DDC) — about 1.5 hours.
> - Activity 2 (optional): a short human-in-the-loop study comparing manual
>   cataloging with reviewing AI-drafted records — about 2 hours.
>
> Compensation: [amount] per hour, paid via [method]. All work is anonymized;
> records are from public-domain/open sources only. No library systems are
> touched. Results will be published in aggregate only.
>
> If interested, reply to this email and we will send the materials and a
> consent form. Thank you for helping make library AI evidence-based!
>
> [Your name, affiliation, contact]

## Protocol notes
- **Counterbalancing (RQ5):** randomize per-cataloger the assignment of records
  to (manual, verify-LLM) conditions and the order of conditions; never let one
  cataloger see the same record in both conditions.
- **Blinding:** catalogers do not know which LLM (if any) drafted a record in
  the verify condition is acceptable — but we do tell them drafts are
  machine-generated (ethical transparency).
- **IAA:** report Cohen's kappa / Krippendorff's alpha between catalogers on the
  validation sample; also report LLM-judge vs. human agreement on faithfulness
  (judge-correlation pilot).
- **Consent & data:** no patron data; works are public domain; store only
  de-identified responses; approval: institutional policy check (likely
  IRB-exempt as professional expert review, but confirm locally).
- **Timeline:** recruit in weeks 1–4 of Phase 1; run validation in weeks 4–5;
  run RQ5 in weeks 10–12.
