---
name: experiment-report
description: >
  Compile optimizer run outputs into a report. Use when asked to write / generate
  / build a report from experiment runs, summarize optimizer runs, turn agent
  outputs into a report, analyze run transcripts, or "make the v-next report."
  Runs a deterministic compiler (per-cell scores, costs, overfit gaps, infra
  audit, mean±std tables) then drives a behavioural fan-out, and bakes in the
  honesty rules learned across v3/v4/v5.
---

# experiment-report

Turns a folder of optimizer **run directories** into a report. Each run dir
(`runs/<target>/spreadsheetbench__…/`) holds `summary.json`, `metadata.json`,
`agent.diff`, and `artifacts/optimize/optimizer_result.json` (the full event
stream). The work splits in two:

- **Deterministic** (scores, costs, overfit gaps, mean±std tables, infra audit) →
  the committed driver **`~/.claude/skills/experiment-report/compile_report.py`**.
- **Behavioural** (what the optimizer *did* and why) → a **fan-out of analysis
  agents** that read the transcripts. The driver prints the fan-out prompt.

Paths below are relative to the **repo root** (`/home/v-tinyantsui/agl-skill`).
Python 3.12 only; no deps beyond stdlib.

## Workflow (the agent path)

**1. Compile.** Point the driver at a glob of run dirs. Pass the pristine-agent
baseline (it usually isn't in the per-cell `summary.json` — read it from the
experiment's `feedback_experiment_docker_*/report.json` `baseline_mean_score`):

```bash
python3 ~/.claude/skills/experiment-report/compile_report.py \
  'runs/spreadsheetbench/spreadsheetbench__*scoretarget*variant-v1*' \
  --baseline 0.192 --title "V1 score-target" --out /tmp/v1_report
```

It writes `/tmp/v1_report/report_data.json` (all per-cell + aggregated facts) and
`report_skeleton.md` (honesty block + mean±std tables + per-cell audit table +
infra audit + the fan-out prompt). The swept axis is **auto-detected** from
whatever varies (target / budget / split / mode), so the same command works for
any experiment shape:

```bash
# budget sweep -> groups by budget, reproduces the plateau
python3 ~/.claude/skills/experiment-report/compile_report.py \
  'runs/spreadsheetbench/spreadsheetbench__*split-long-80-40-280*' --baseline 0.125 --out /tmp/budg
```

**2. Read the INFRA AUDIT first.** The skeleton lists cells with gen-phase drops
or near-zero held-out — those scores are **contaminated** (relay down / throttle /
empty outputs), not the optimizer making a bad agent. Exclude or footnote them
*before* you interpret anything. (A near-zero with 0 drops but a 60-second 280-task
validation is the medium-reasoning burst-collapse — same class; check `gen_tasks`/
wall in `report_data.json`.)

**3. Fan out the behavioural analysis.** The skeleton ends with a ready prompt.
Spawn one analysis agent **per group** (or per theme) with the Agent tool, swapping
in that group's glob. Each agent parses the `raw` streams (never Reads them whole)
and returns a ~600-word section with `raw[<index>]` citations. Paste the sections
back.

**4. Assemble.** Combine: the mean±std tables (from the skeleton), the behavioural
sections (from the fan-out), and a synthesis — and run the **honesty checklist**
below over the draft before finishing.

## The honesty checklist (do not skip — these are corrected mistakes)

The driver prints these into every skeleton; verify the final report obeys them:

- A **cell = one stochastic roll**. Report **mean±std (n)**, never a lone cell as
  truth. With small n, no single number / no A-vs-B / budget / target *ranking* is
  supported beyond effects that **repeat across rolls AND have a trace mechanism**.
- **Don't privilege** one config as "more reliable" at equal n (the v3 error).
- **No causal arrows** between different metrics (val→test).
- **Cost in iterations / self-scores / tokens, never wall-clock** (throttle-
  contaminated).
- **Infra ≠ result**: audit gen drops; a throttled 0 is not a capability 0.
- **Cite `raw[index]` / `agent.diff`** evidence.
- **Explain jargon** (self-score, `--limit`, "cell") on first use.
- Lens: the self-score is a flawed proxy on **scale** (few tasks → misses
  held-out-scale failures) and **identity** (same-distribution → overstates
  held-out).

## Gotchas (things that bit me building this)

- **Baseline isn't in per-cell `summary.json`.** The orchestrator computes one
  shared baseline; pass `--baseline` from the experiment `report.json`.
- **Budget isn't in `run_params`** — it's the `bNNm`/`bnolimit` token in the dir
  name. The driver pulls it from there; grouping is by *varying* facets only.
- **"Best self-score" must be full-train.** A `--limit 1` probe reads 1.0 and
  would fake a huge overfit gap; the driver only counts self-scores with no
  `--limit` or `--limit ≥ 60`.
- **`timed_out` is NOT contamination.** Blind budget cells time out *normally*
  (they run the clock); score-target cells timing out means the safety cap cut
  them off (a config bug — score-target should be `--safety-cap-seconds none`).
  So `timed_out` is shown per-cell but never auto-flagged as suspect.
- **A "broken agent" is often infra.** The v4 "broken" V3 cell (0.004) was the
  relay buckling during validation (280 tasks in 68 s, copy-input fallback), not a
  bad edit — always check the audit before calling a near-zero a real failure.
- The `raw` event stream is huge; the driver and the fan-out agents **parse it with
  python**, never Read it whole into context.

## Verify

```bash
uvx --from 'ruff==0.15.*' ruff check ~/.claude/skills/experiment-report/compile_report.py
python3 ~/.claude/skills/experiment-report/compile_report.py \
  'runs/spreadsheetbench/spreadsheetbench__*scoretarget*variant-v1*' --baseline 0.192 --out /tmp/check
# -> "wrote /tmp/check/... (12 cells, 4 groups, 1 suspect)"; groups = target=0.6..0.9
```
