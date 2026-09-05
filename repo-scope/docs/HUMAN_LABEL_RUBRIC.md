# RepoScope human risk labelling rubric

This rubric defines how an independent human reviewer assigns `healthy`, `watch`, or `risky` to a repository snapshot without copying RepoScope's deterministic health score, weak-label output, or ML prediction.

## Purpose

Human review is the independent reference used to audit weak supervision and determine whether the ML model generalizes beyond its automated label sources. Reviewers judge the repository at the snapshot date, not with hindsight from later events.

## Blinding rules

Before assigning a label, a reviewer must not be shown:

- RepoScope health score or health label;
- weak label or weak-label source;
- ML prediction, probability, confidence, or feature importance;
- review-queue reasons that reveal weak-label boundary logic;
- another reviewer's decision before submitting their own.

A reviewer may inspect public repository evidence that a real maintainer or engineering team could observe: maintenance statements, repository activity, releases, unresolved issues, pull-request flow, contributor continuity, documentation, CI status, tests, deprecation notices, and related public context.

## Labels

### `healthy`

Use `healthy` when the repository shows credible ongoing maintenance and low near-term continuity risk. Supporting evidence can include meaningful recent maintenance, an appropriate release cadence, responsive issue/PR handling, contributor continuity, working engineering controls, current documentation, and no abandonment/deprecation signal.

A project does not need to be highly popular or commit every week to be healthy. Mature stable projects may have a slower cadence.

### `watch`

Use `watch` when the repository remains usable or plausibly maintained but shows material warning signs. Examples include a clear slowdown relative to historical cadence, increasingly stale releases, growing unanswered work, concentrated ownership, degrading CI/tests/docs, a transition period, or mixed continuity evidence.

Use `watch` when evidence is genuinely mixed rather than forcing an overconfident extreme label.

### `risky`

Use `risky` when strong evidence suggests substantial maintenance or continuity risk: explicit archive/deprecation/abandonment, end-of-support statements, prolonged inconsistent inactivity with unresolved work, unattended critical issues/PRs, loss of maintainer base, obsolete dependency/release state without a maintenance path, or practical abandonment despite the repository remaining open.

Do not use `risky` merely because a repository is small, old, unpopular, or single-maintainer.

## Review procedure

For each candidate:

1. Confirm repository and snapshot timestamp.
2. Inspect maintenance, archival, replacement, and deprecation statements.
3. Compare recent commits with historical cadence.
4. Inspect release/support cadence.
5. Inspect issue and PR responsiveness, not only counts.
6. Inspect contributor continuity.
7. Use CI/tests/documentation as supporting evidence.
8. Assign exactly one label: `healthy`, `watch`, or `risky`.
9. Write concise evidence-based `review_notes`.
10. Submit under a stable `reviewer` identifier.

If there is not enough evidence for a defensible judgement, skip the candidate rather than inventing a label.

## Blind reviewer assignment planner

When real reviewer identifiers are available, create a controlled overlap before review begins. The default plan gives each reviewer 100 repositories and shares 60 repositories across reviewers so inter-reviewer agreement can be measured on the required overlap:

```bash
python scripts/build_human_review_assignments.py \
  --reviewers reviewer-a reviewer-b \
  --per-reviewer 100 \
  --overlap 60
```

The generated `data/repo_risk_human_review_assignments.csv` contains only `reviewer` and `repo`. It does not contain weak labels, model outputs, health scores, review reasons, or human decisions. Repository rows are deduplicated before assignment, shared overlap is deterministic, and reviewer-specific remainder sets are disjoint when queue capacity allows.

Do not create assignments with invented reviewer identities. The identifiers must represent real independent reviewers.

## Independent blind review CLI

Run from `repo-scope/` with the assignment file:

```bash
python scripts/review_human_labels.py \
  --reviewer reviewer-a \
  --assignments data/repo_risk_human_review_assignments.csv \
  --limit 20
```

Without `--assignments`, the CLI can still review the full pending queue. With assignments enabled, each reviewer only sees repositories assigned to them.

The CLI hides automation-derived fields and writes each independent decision to:

`data/repo_risk_human_review_decisions.csv`

Multiple reviewers may review the same repository independently. The same reviewer cannot silently overwrite their own earlier decision; a correction requires an explicit replacement operation. Decisions from different reviewers are preserved side-by-side.

Raw decision fields are:

- `repo`
- `human_label`
- `review_notes`
- `reviewer`
- `reviewed_at_utc`

Evidence notes and the review timestamp are mandatory integrity fields. The adjudication path rejects a raw decision if either is missing, even if the CSV was edited outside the CLI.

The tool does not inspect repositories or choose labels automatically. Human evidence review is required.

## Inter-reviewer reliability

After at least two reviewers have overlapping decisions, generate the agreement audit with:

```bash
python scripts/report_reviewer_agreement.py
```

The report is written to:

`data/repo_risk_human_reviewer_agreement.json`

It records reviewer counts, shared repositories, raw pairwise agreement, Cohen's kappa, disagreement counts, invalid labels, and duplicate reviewer/repository decisions. Cohen's kappa is computed only for reviewer pairs with shared repositories. This audit measures human-label reliability and never promotes the model by itself.

## Adjudication

Raw independent decisions are not used directly as model ground truth. Produce the durable adjudicated registry with:

```bash
python scripts/adjudicate_human_reviews.py
```

The adjudicator requires at least two independent reviewers per repository. It writes a durable label only when there is a strict majority. Ties and unresolved disagreement remain excluded instead of being guessed.

Adjudicated labels are written to:

`data/repo_risk_human_labels.csv`

A machine-readable adjudication audit is written to:

`data/repo_risk_human_adjudication.json`

The audit records whether there are no decisions, partial adjudication, or fully adjudicated evidence, along with insufficient-review and disagreement repositories. Original decisions remain preserved in `data/repo_risk_human_review_decisions.csv`, so disagreement stays auditable.

## Evidence hierarchy

Prefer direct evidence over proxies:

1. explicit maintainer statement or archive/deprecation state;
2. concrete maintenance activity and response patterns;
3. release/support cadence;
4. contributor continuity;
5. engineering-practice signals;
6. popularity only as context, never as the deciding signal.

Stars, forks, repository age, language, and organization prestige must not determine the label.

## Quality-control protocol

For validation used to judge model quality:

- use at least two independent reviewers per repository where practical;
- keep reviewers blind to automation and to each other's decisions;
- preserve all raw decisions;
- use controlled reviewer assignments to guarantee sufficient overlap without leaking automated signals;
- measure reviewer agreement separately from weak-vs-human agreement;
- use raw agreement and Cohen's kappa to audit reviewer consistency;
- route disagreements to explicit adjudication rather than silent overwrite;
- persist adjudication status and unresolved cases as a machine-readable audit artifact;
- stratify reviewed repositories across language, popularity, archived/active state, and maintenance cadence;
- never treat weak-label performance alone as independent validation.

## Ground-truth boundary

`data/repo_risk_human_review_queue.csv` is only a candidate list.

`data/repo_risk_human_review_assignments.csv` is an operational reviewer/repository routing file; it is not ground truth.

`data/repo_risk_human_review_decisions.csv` contains independent raw reviewer decisions.

`data/repo_risk_human_reviewer_agreement.json` audits inter-reviewer reliability and is not ground truth.

`data/repo_risk_human_adjudication.json` records adjudication state and unresolved cases; it is an audit artifact, not a label source.

`data/repo_risk_human_labels.csv` contains only adjudicated durable labels eligible to enter the combined training/validation path.

Allowed labels are exactly `healthy`, `watch`, and `risky`. RepoScope must never fabricate human decisions or automatically convert weak labels into human ground truth.
