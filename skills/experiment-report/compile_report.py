#!/usr/bin/env python3
"""Compile optimizer run outputs into a report skeleton.

Takes the per-run directories an experiment produced (each with summary.json,
metadata.json, agent.diff, and artifacts/optimize/optimizer_result.json) and:

  1. Extracts per-cell facts: held-out score, baseline, the swept-axis value
     (budget / score-target / split / mode), self-score trajectory + best,
     overfit gap (best self-score - held-out), COST in iterations/self-scores/
     output-tokens (NOT wall-clock), gen-phase drops (agent_errors), timing.
  2. Groups by the detected swept axis and aggregates mean +/- sample-std (n).
  3. Flags infra contamination (gen drops, timeouts, near-zero scores) so a
     throttle-deflated 0 is never mistaken for a real low score.
  4. Emits report_data.json (all of the above) and report_skeleton.md: the
     aggregated tables, the per-cell table, the HONESTY RULES (baked in), a
     ready-to-paste fan-out prompt for the behavioural sections, and an
     infra-vs-experiment audit.

The behavioural narrative is NOT scripted here -- that needs the fan-out agents
(SKILL.md drives that). This produces everything deterministic + the scaffold.

Usage:
  compile_report.py '<glob of run dirs>' [--out DIR] [--title STR]
  e.g. compile_report.py 'runs/spreadsheetbench/spreadsheetbench__*variant-v1*'
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics as st
from collections import defaultdict

# The report-writing rules distilled from rounds of human feedback on v3/v4/v5.
# Baked into every skeleton so the report can't drift back into the mistakes
# that got corrected.
HONESTY_RULES = """\
> **Read this first -- what this report can and cannot claim.**
>
> - A **cell** is one *stochastic* optimizer roll of one condition. The held-out
>   score is averaged over all held-out tasks (well-sampled), but reflects a
>   **single roll** -- a re-run with a new seed lands elsewhere. Report the
>   per-condition **mean +/- sample-std (n)**, never a lone cell number as if it
>   were the truth.
> - With small n, **no single cell, and no A-vs-B / budget / target ranking, is
>   statistically supported** beyond effects that (a) repeat across independent
>   rolls AND (b) have a mechanism visible in the traces. Say so.
> - **Do not privilege** one config/run as "more reliable" than another at the
>   same n -- they are equally few rolls. (This is the exact error that got
>   called out in v3.)
> - **No causal arrows between different metrics** (e.g. val -> test). They are
>   separate measurements, not a pipeline.
> - **Report COST in iterations / self-scores / output-tokens, NOT wall-clock.**
>   Wall-clock is contaminated by relay speed and throttling.
> - **Separate infra failures from experiment results.** A near-zero score from a
>   throttled/empty generation (dropped tasks, API outage, 503, relay down) is
>   NOT a real low score. Always report gen-phase `agent_errors` next to any
>   score; audit them before interpreting.
> - **Cite file:line evidence** into the transcripts: an array index into a run's
>   `artifacts/optimize/optimizer_result.json` `raw[...]`, or `agent.diff`.
> - Explain jargon on first use: **self-score** = the optimizer's only signal,
>   the agent scored on a slice of *train*; **--limit N** = how many train tasks
>   that self-score ran on; a **cell** = one condition x one roll.
> - Interpretive lens (the v5 meta-finding): the self-score is a flawed proxy on
>   two axes -- **scale** (measured on few tasks -> misses held-out-scale burst
>   failures) and **identity** (same-distribution -> overstates held-out). Most
>   successes and failures trace to one of these.
"""


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def parse_optimizer_result(d):
    """Cost + self-score signals from the raw event stream (no whole-file read into a report)."""
    res = _load(os.path.join(d, "artifacts", "optimize", "optimizer_result.json"))
    out = {
        "edits": 0,
        "self_scores": 0,
        "best_self": None,
        "self_trajectory": [],
        "out_tokens": None,
        "wall_s": None,
        "timed_out": None,
        "stop_variant": None,
        "score_target": None,
        "predicted_heldout": None,
        "new_fns": [],
    }
    if not res:
        return out
    out["wall_s"] = res.get("wall_clock_seconds")
    out["timed_out"] = res.get("timed_out")
    out["stop_variant"] = res.get("stop_variant")
    out["score_target"] = res.get("score_target")
    tok = res.get("token_usage") or {}
    out["out_tokens"] = tok.get("output_tokens") or tok.get("output")
    raw = res.get("raw") or []
    last_was_selfscore = False
    last_was_full = False
    full_trajectory = []
    for ev in raw:
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                bt = b.get("type")
                if bt == "tool_use":
                    name = b.get("name")
                    if name in ("Edit", "Write", "MultiEdit"):
                        out["edits"] += 1
                    elif name == "Bash":
                        cmd = b.get("input", {}).get("command", "")
                        if "run_baseline" in cmd and "codegen_handoff" in cmd:
                            out["self_scores"] += 1
                            last_was_selfscore = True
                            # full-train self-score = no --limit, or a large --limit
                            # (probes use --limit 1/2/30; full uses none or >=60).
                            m = re.search(r"--limit\s+(\d+)", cmd)
                            last_was_full = (m is None) or (int(m.group(1)) >= 60)
        elif ev.get("type") == "user":
            for b in ev.get("message", {}).get("content", []) or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    txt = b.get("content", "")
                    if isinstance(txt, list):
                        txt = " ".join(str(x.get("text", "")) for x in txt if isinstance(x, dict))
                    m = re.search(r'"?mean_score"?["\s:]+([0-9.]+)', str(txt))
                    if m and last_was_selfscore:
                        sc = float(m.group(1))
                        out["self_trajectory"].append(sc)
                        if last_was_full:
                            full_trajectory.append(sc)
                        last_was_selfscore = False
    # Prefer the best FULL-train self-score (the meaningful objective); a tiny
    # --limit 1 probe reads 1.0 and is noise, so don't let it inflate the gap.
    if full_trajectory:
        out["best_self"] = max(full_trajectory)
    elif out["self_trajectory"]:
        out["best_self"] = max(out["self_trajectory"])
    # PREDICTED_HELDOUT (V3 calibration), if present in the final text
    blob = json.dumps(raw) + (res.get("text") or "")
    m = re.search(r"PREDICTED_HELDOUT[:\s]+([0-9.]+)", blob)
    if m:
        out["predicted_heldout"] = float(m.group(1))
    # new functions in the agent source (filter out _self generated solutions)
    diff = _read_text(os.path.join(d, "agent.diff"))
    if diff:
        keep = False
        for line in diff.splitlines():
            if line.startswith("diff --git"):
                keep = bool(re.search(r"/sheet_agent/(agents|run_baseline)\.py", line)) and "_self" not in line
            elif keep:
                m = re.match(r"\+\s*(?:async )?def ([a-z_][a-z0-9_]*)", line)
                if m:
                    out["new_fns"].append(m.group(1))
    return out


def _read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def gen_audit(d):
    """Gen-phase drop audit: a near-zero score with many agent_errors is infra, not capability."""
    for rel in ("validation_outputs", "test_outputs"):
        p = os.path.join(d, "artifacts", rel, "results.jsonl")
        if not os.path.exists(p):
            continue
        total = errors = throttle = 0
        for line in _read_text(p).splitlines():
            if '"agent_error": "' in line:
                errors += 1
                if re.search(r"RateLimit|APITimeout|ServiceUnavailable|503|InternalServer|ConnectionRefused", line):
                    throttle += 1
            if line.strip():
                total += 1
        return {"tasks": total, "drops": errors, "throttle_drops": throttle}
    return {"tasks": None, "drops": None, "throttle_drops": None}


def extract_facets(basename, params):
    """Experimental facets of a cell (everything except the replicate index).
    Pulls run_params plus the budget slug from the dir name (budget isn't in
    run_params). The swept axis is whichever of these VARIES across the cell set."""
    f = {}
    for k, v in (params or {}).items():
        if k in ("rep", "codegen"):  # rep is the replicate; codegen is a relay label, not the axis
            continue
        f[k] = str(v)
    m = re.search(r"__b(\d+m|nolimit)__", basename)
    if m:
        f["budget"] = "b" + m.group(1)
    return f


def extract_cell(d):
    summ = _load(os.path.join(d, "summary.json")) or {}
    meta = _load(os.path.join(d, "metadata.json")) or {}
    opt = parse_optimizer_result(d)
    held = None
    fv = summ.get("final_validation") or {}
    ft = summ.get("final_test") or {}
    held = ft.get("mean_score") if ft.get("mean_score") is not None else fv.get("mean_score")
    held_kind = "test" if ft.get("mean_score") is not None else "val"
    baseline = (summ.get("baseline_train") or {}).get("mean_score")
    params = meta.get("run_params") or {}
    audit = gen_audit(d)
    gap = (opt["best_self"] - held) if (opt["best_self"] is not None and held is not None) else None
    # budget the cell was actually given (silent cap or none), for context
    return {
        "dir": os.path.basename(d),
        "params": params,
        "facets": extract_facets(os.path.basename(d), params),
        "group": None,  # assigned in main from the varying facets
        "held_out": held,
        "held_kind": held_kind,
        "baseline": baseline,
        "best_self": opt["best_self"],
        "overfit_gap": gap,
        "edits": opt["edits"],
        "self_scores": opt["self_scores"],
        "out_tokens": opt["out_tokens"],
        "wall_s": opt["wall_s"],
        "timed_out": opt["timed_out"],
        "stop_variant": opt["stop_variant"],
        "score_target": opt["score_target"],
        "predicted_heldout": opt["predicted_heldout"],
        "new_fns": opt["new_fns"],
        "gen_tasks": audit["tasks"],
        "gen_drops": audit["drops"],
        "gen_throttle_drops": audit["throttle_drops"],
    }


def agg(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    if not xs:
        return None
    mean = sum(xs) / len(xs)
    sd = st.stdev(xs) if len(xs) > 1 else 0.0
    return {"n": len(xs), "mean": round(mean, 4), "std": round(sd, 4), "values": [round(x, 4) for x in xs]}


def fmt(a):
    return f"{a['mean']:.3f}+/-{a['std']:.3f} (n={a['n']})" if a else "n/a"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("glob", help="glob of run dirs (quote it), e.g. 'runs/spreadsheetbench/spreadsheetbench__*variant-v1*'")
    ap.add_argument("--out", default=None, help="output dir (default: ./report_out)")
    ap.add_argument("--title", default="Experiment report")
    ap.add_argument("--baseline", type=float, default=None,
                    help="pristine-agent baseline (cells often lack it; pass it from the experiment report.json)")
    args = ap.parse_args()

    dirs = [d for d in sorted(glob.glob(args.glob)) if os.path.isfile(os.path.join(d, "summary.json"))]
    if not dirs:
        print(f"No run dirs (with summary.json) match: {args.glob}")
        return 1
    cells = [extract_cell(d) for d in dirs]

    # Auto-detect the swept axis: the facets that VARY across the cell set.
    allkeys = set().union(*(c["facets"].keys() for c in cells)) if cells else set()
    varying = [k for k in sorted(allkeys) if len({c["facets"].get(k) for c in cells}) > 1]
    for c in cells:
        c["group"] = "/".join(f"{k}={c['facets'][k]}" for k in varying if k in c["facets"]) or "all"

    groups = defaultdict(list)
    for c in cells:
        groups[c["group"]].append(c)
    summary_by_group = {}
    for g, cs in sorted(groups.items()):
        summary_by_group[g] = {
            "n": len(cs),
            "held_out": agg([c["held_out"] for c in cs]),
            "best_self": agg([c["best_self"] for c in cs]),
            "overfit_gap": agg([c["overfit_gap"] for c in cs]),
            "edits": agg([c["edits"] for c in cs]),
            "self_scores": agg([c["self_scores"] for c in cs]),
            "out_tokens": agg([c["out_tokens"] for c in cs]),
            "predicted_heldout": agg([c["predicted_heldout"] for c in cs]),
        }

    # Infra audit: cells whose SCORE is likely contaminated (don't average in).
    # gen drops = throttle/outage dropped tasks; near-zero held-out usually means
    # the generation collapsed (relay down / empty outputs), not a bad agent.
    # (timed_out alone is NOT a contamination signal -- blind budget cells time
    # out normally; it's shown per-cell for context.)
    suspect = [
        c for c in cells
        if (c["gen_drops"] or 0) > 0
        or (c["held_out"] is not None and c["held_out"] < 0.05)
    ]

    out_dir = args.out or "report_out"
    os.makedirs(out_dir, exist_ok=True)
    baseline = args.baseline
    if baseline is None:
        baseline = next((c["baseline"] for c in cells if c["baseline"] is not None), None)
    data = {
        "title": args.title,
        "n_cells": len(cells),
        "baseline": baseline,
        "summary_by_group": summary_by_group,
        "cells": cells,
        "suspect_cells": [c["dir"] for c in suspect],
    }
    with open(os.path.join(out_dir, "report_data.json"), "w") as fh:
        json.dump(data, fh, indent=2)

    # ---- markdown skeleton ----
    L = []
    L.append(f"# {args.title}\n")
    L.append(HONESTY_RULES + "\n")
    L.append(f"Baseline (pristine agent): **{round(baseline, 3) if baseline is not None else 'n/a'}**. "
             f"{len(cells)} cells across {len(groups)} group(s).\n")

    L.append("## Results by group (mean +/- std)\n")
    has_pred = any(g["predicted_heldout"] for g in summary_by_group.values())
    head = "| group | held-out | best self-score | overfit gap | edits | self-scores |"
    if has_pred:
        head = "| group | held-out | predicted | best self-score | overfit gap | edits |"
    L.append(head)
    L.append("|" + "---|" * (head.count("|") - 1))
    for g, s in summary_by_group.items():
        if has_pred:
            L.append(f"| {g} | {fmt(s['held_out'])} | {fmt(s['predicted_heldout'])} | "
                     f"{fmt(s['best_self'])} | {fmt(s['overfit_gap'])} | {fmt(s['edits'])} |")
        else:
            L.append(f"| {g} | {fmt(s['held_out'])} | {fmt(s['best_self'])} | "
                     f"{fmt(s['overfit_gap'])} | {fmt(s['edits'])} | {fmt(s['self_scores'])} |")
    L.append("")

    L.append("## Per-cell (audit before interpreting)\n")
    L.append("| dir (tail) | group | held | best-self | gap | edits | self | gen drops | timed_out |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        tail = c["dir"].split("__split-")[-1] if "__split-" in c["dir"] else c["dir"][-40:]
        L.append(f"| {tail} | {c['group']} | {c['held_out']} | {c['best_self']} | "
                 f"{c['overfit_gap']} | {c['edits']} | {c['self_scores']} | "
                 f"{c['gen_drops']}/{c['gen_tasks']} | {c['timed_out']} |")
    L.append("")

    if suspect:
        L.append("## INFRA AUDIT -- treat these cells with suspicion (not real results)\n")
        for c in suspect:
            why = []
            if c["gen_drops"]:
                why.append(f"{c['gen_drops']} gen drops ({c['gen_throttle_drops']} throttle)")
            if c["timed_out"]:
                why.append("timed_out")
            if c["held_out"] is not None and c["held_out"] < 0.05:
                why.append(f"near-zero held-out ({c['held_out']})")
            L.append(f"- `{c['dir']}` -- {', '.join(why)}")
        L.append("\nA near-zero score with many gen drops is an infra failure (relay/throttle), "
                 "NOT the optimizer producing a bad agent. Exclude or footnote; do not average in blindly.\n")

    L.append("## Behavioural analysis -- FAN OUT (fill these in)\n")
    L.append("Spawn one analysis agent per group (or per theme). Paste this prompt, "
             "swapping the glob/questions. Each returns a markdown section with `raw[...]` citations:\n")
    L.append("""```
Analyze the BEHAVIOUR of the optimizer in these runs: <glob>.
Each dir has artifacts/optimize/optimizer_result.json (`raw` event stream -- PARSE with
python, do NOT Read whole), agent.diff, summary.json (held-out score). For each cell:
what did it build (agent.diff new fns)? how many edits/self-scores? did it stop on the
merits or run out? best self-score vs held-out (overfit gap)? Then synthesize the group:
the behavioural signature, why the held-out lands where it does, the failure modes.
Cite `<dir-basename>/artifacts/optimize/optimizer_result.json` raw[<index>]. Be honest
about n. Return a ~600-word markdown section. Your message IS the deliverable.
```\n""")

    L.append("## Synthesis (write last)\n")
    L.append("- Lead with what survives the honesty rules: effects that repeat across rolls "
             "AND have a mechanism in the traces.\n- Tie failures back to the self-score being a "
             "flawed proxy (scale + identity).\n- End with implications, not a leaderboard.\n")

    with open(os.path.join(out_dir, "report_skeleton.md"), "w") as fh:
        fh.write("\n".join(L))

    print(f"wrote {out_dir}/report_data.json + report_skeleton.md "
          f"({len(cells)} cells, {len(groups)} groups, {len(suspect)} suspect)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
