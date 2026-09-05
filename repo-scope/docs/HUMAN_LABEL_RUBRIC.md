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

## Independent blind review CLI

Run from `repo-scope/`:

```bash
python scripts/review_human_labels.py --reviewer reviewer-a --limit 20
```

The CLI hides automation-derived fields and writes each independent decision to:

`data/repo_risk_human_review_decisions.csv`

Multiple reviewers may review the same repository independently. The same reviewer cannot silently overwrite their own earlier decision; a correction requires an explicit replacement operation. Decisions from different reviewers are preserved side-by-side.

Raw decision fields are:

- `repo`
- `human_label`
- `review_notes`
- `reviewer`
- `reviewed_at_utc`

The tool does not inspect repositories or choose labels automatically. Human evidence review is required.

## Adjudication

Raw independent decisions are not used directly as model ground truth. Produce the durable adjudicated registry with:

```bash
python scripts/adjudicate_human_reviews.py
```

The adjudicator requires at least two independent reviewers per repository. It writes a durable label only when there is a strict majority. Ties and unresolved disagreement remain excluded instead of being guessed.

Adjudicated labels are written to:

`data/repo_risk_human_labels.csv`

Original decisions remain preserved in `data/repo_risk_human_review_decisions.csv`, so disagreement stays auditable.

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
- measure reviewer agreement separately from weak-vs-human agreement;
- route disagreements to explicit adjudication rather than silent overwrite;
- stratify reviewed repositories across language, popularity, archived/active state, and maintenance cadence;
- never treat weak-label performance alone as independent validation.

## Ground-truth boundary

`data/repo_risk_human_review_queue.csv` is only a candidate list.

`data/repo_risk_human_review_decisions.csv` contains independent raw reviewer decisions.

`data/repo_risk_human_labels.csv` contains only adjudicated durable labels eligible to enter the combined training/validation path.

Allowed labels are exactly `healthy`, `watch`, and `risky`. RepoScope must never fabricate human decisions or automatically convert weak labels into human ground truth.
