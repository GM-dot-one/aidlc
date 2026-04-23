# Workflow reference

Each stage is a pure Python function in `aidlc/workflows/`. The CLI
(`aidlc/cli.py`) is a thin shell that wires env-driven clients into them.

## Stage 1 — `idea_to_spec`

**Input:** a work package with a rough, human-written description (the raw
"idea").
**Output:** the same work package, but with its description replaced by a
structured spec (problem, user story, acceptance criteria, risks, open
questions, size). Status is advanced to the first matching one of
`Specified / In specification / Ready for dev / Confirmed`.

**Prompt:** [`aidlc/prompts/idea_to_spec.md`](../aidlc/prompts/idea_to_spec.md).
Hard-coded instruction that the model must respond with JSON only.
`extract_json` is forgiving about fences and preambles but **will** raise
if the model went fully off-script — better to fail loudly than silently
write garbage to the ticket.

**Run:**
```bash
aidlc spec 1234
aidlc spec 1234 --force   # re-run even if already done
```

**Idempotency:** guarded by `db.has_run("idea_to_spec", wp_id)`. `--force`
bypasses. The patch also preserves the original idea text under an
`## Original idea` separator so the source isn't lost.

---

## Stage 2 — `spec_to_tasks`

**Input:** a work package whose description contains a spec markdown block
(typically produced by stage 1).
**Output:** N new child work packages linked to the parent, each carrying
a definition-of-done and dependency annotations.

**Prompt:** [`aidlc/prompts/spec_to_tasks.md`](../aidlc/prompts/spec_to_tasks.md).

**Why "vertical slice" in the prompt?** Horizontal decomposition (all
routes → all validators → all tests) is what LLMs do by default and
produces tasks that can't be demo'd independently. Explicit "prefer
vertical slices" guidance shifts the output dramatically.

**Type resolution:** the LLM may suggest `Feature`, `User story`, etc.
The agent resolves those against OpenProject's `/api/v3/types` and falls
back to `Task` if unknown.

**Run:**
```bash
aidlc decompose 1234
```

---

## Stage 3 — `task_to_code`

**Input:** a child task work package.
**Output:** a branch + commits + draft PR on the configured GitHub repo,
with the PR body linked back to the work package ID.

**Prompt:** [`aidlc/prompts/task_to_code.md`](../aidlc/prompts/task_to_code.md).

**Constraints baked into the prompt:**
- Must respond with a JSON plan (`branch_name`, `commit_message`,
  `pr_title`, `pr_body`, `files[]`).
- Prefers scaffolding + failing tests over faking a full implementation.
- PR body must include a `## What this does not do` section listing
  outstanding acceptance criteria.

**Safety:**
- Branches are always prefixed `aidlc/` so your PR rules can scope on them.
- Branch names are sanitised (`/`, alphanumerics, `.`, `_`, `-`; ≤100 chars).
- Plans with >10 files are rejected.
- PRs are opened as **drafts**.

**Run:**
```bash
aidlc code 1235
aidlc code 1235 --hints "Ruby on Rails + RSpec"
```

---

## Stage 4 — `status_updates`

**Input:** the SQLite snapshot of tracked work packages (populated by
stage 3). No LLM call.
**Output:** transitions + comments on OpenProject work packages when their
linked PR/CI state changes.

**Transitions:**

| Event | Action |
|---|---|
| PR merged | WP → `Closed`/`Done`/`Resolved`, comment "PR merged." |
| PR closed, not merged | WP → `In progress`/`Rejected`, comment "Closed without merging." |
| CI newly failed | Comment "CI failed on commit X." (no status change) |
| CI newly passed | WP → `In review`/`Code review`, comment "Ready for human review." |
| Nothing changed | No-op (snapshot untouched) |

**Run:**
```bash
aidlc watch                # one tick
```

**Scheduling:** wrap in cron or a systemd timer. Every 2-5 minutes is
plenty — GitHub's check-runs endpoint has generous rate limits and the
agent no-ops on unchanged work.

```cron
*/5 * * * * cd /path/to/aidlc && /usr/bin/env -i bash -lc "aidlc watch"
```

---

## End-to-end

```bash
aidlc run-all 1234                 # stages 1 → 2 → 3 on the first child
aidlc run-all 1234 --skip-code     # stop after decompose (useful for review)
```
