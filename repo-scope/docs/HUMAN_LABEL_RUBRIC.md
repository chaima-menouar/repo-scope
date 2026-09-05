# RepoScope human risk labelling rubric

This rubric defines how a human reviewer should assign `healthy`, `watch`, or `risky` to a repository snapshot without copying RepoScope's deterministic health score, weak-label rule, or ML prediction.

## Purpose

Human labels are the independent reference set used to audit weak supervision and, eventually, validate whether the ML model generalizes beyond its automated label sources.

A reviewer should judge the repository **at the snapshot date**, not based on what happened later.

## Blinding rules

Before assigning a label, the reviewer should not be shown:

- RepoScope health score or health label;
- weak label or weak-label source;
- ML prediction, probability, or feature importance;
- another reviewer's label before making an independent judgement.

The reviewer may inspect public repository evidence that a real maintainer or engineering team could observe, including repository activity, releases, unresolved issues, pull-request flow, contributor continuity, documentation, CI status, tests, deprecation notices, and maintenance statements.

## Labels

### `healthy`

Use `healthy` when the repository shows credible evidence of ongoing maintenance and low near-term continuity risk.

Typical evidence includes several of the following:

- recent, meaningful development or maintenance activity;
- releases or versioned delivery that appear current for the project's normal cadence;
- issues and pull requests receiving responses or resolution;
- more than one active contributor, or a clearly supported single-maintainer project with continuity evidence;
- CI/tests or other engineering controls that reduce regression risk;
- documentation that matches the current state of the project;
- no clear deprecation, archival, abandonment, or replacement notice.

A repository does **not** need to be highly popular or commit every week to be healthy. Mature, stable projects can have a slower cadence.

### `watch`

Use `watch` when the repository is still usable or plausibly maintained, but there are material warning signs that deserve monitoring.

Typical evidence includes one or more of the following:

- maintenance activity has slowed substantially relative to the project's prior cadence;
- releases are becoming stale while the repository is not explicitly archived;
- issue or pull-request backlog is growing with limited maintainer response;
- contributor activity is concentrated in one person with little visible continuity;
- CI/tests/documentation are incomplete or degrading;
- maintenance status is ambiguous or the project appears to be in a transition period;
- there is conflicting evidence: some recent activity exists, but multiple continuity signals are weak.

Use `watch` instead of forcing a confident `healthy` or `risky` label when the evidence is mixed.

### `risky`

Use `risky` when there is strong evidence that depending on the repository carries substantial maintenance or continuity risk.

Typical evidence includes one or more strong signals, especially when combined:

- repository is explicitly archived, deprecated, abandoned, or replaced;
- maintainers state that support has ended or development has stopped;
- prolonged inactivity is inconsistent with the project's historical cadence and unresolved work remains;
- critical issues or pull requests remain unattended for a long period;
- the project has effectively lost its maintainer/contributor base;
- release/dependency state is clearly obsolete and there is no credible maintenance path;
- the repository is still technically open but evidence strongly indicates practical abandonment.

Do not use `risky` merely because a repository is small, unpopular, old, or maintained by one person.

## Review procedure

For each candidate repository:

1. Record the repository name and snapshot timestamp.
2. Inspect maintenance/deprecation notices first.
3. Review recent commits and compare them with the repository's historical cadence.
4. Inspect releases/tags and whether delivery appears current for this project type.
5. Inspect issue and pull-request responsiveness, not only raw counts.
6. Inspect contributor continuity and obvious single-maintainer dependency.
7. Inspect CI/tests/documentation as supporting evidence.
8. Assign exactly one label: `healthy`, `watch`, or `risky`.
9. Write a short evidence-based `review_notes` explanation.
10. Record `reviewer` and `reviewed_at_utc`.

## Evidence hierarchy

Prefer direct repository evidence over proxies:

1. explicit maintainer statement or archive/deprecation state;
2. concrete maintenance activity and response patterns;
3. release/support cadence;
4. contributor continuity;
5. engineering-practice signals;
6. popularity metrics only as context, never as the deciding signal.

Stars, forks, repository age, programming language, and organization prestige must not determine the label.

## Ambiguous cases

If the evidence is genuinely mixed, prefer `watch` and explain the conflict in `review_notes`.

If there is too little evidence to make a defensible judgement, do not invent a label. Leave the repository unreviewed and note why outside the durable label registry until sufficient evidence is available.

## Quality-control protocol

For the validation subset used to judge model quality:

- use at least two independent reviewers where practical;
- keep reviewers blind to automated labels and model output;
- measure raw agreement and Cohen's kappa when two reviewers label the same subset;
- adjudicate disagreements using the written evidence, not majority intuition alone;
- preserve the original reviewer decisions when producing an adjudicated label so disagreement remains auditable;
- stratify reviewed repositories across language, popularity, archived/active state, and maintenance cadence.

Human-reviewed labels should be evaluated separately from weak labels. A model that performs well only on weak labels is not considered validated.

## Durable label registry

Approved human labels belong in:

`data/repo_risk_human_labels.csv`

Expected fields:

- `repo`
- `label`
- `review_notes`
- `reviewer`
- `reviewed_at_utc`

Allowed labels are exactly `healthy`, `watch`, and `risky`.

The generated review queue is only a candidate list and must never be treated as the durable source of human ground truth.
