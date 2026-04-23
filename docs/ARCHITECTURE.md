# Architecture

## Design goals

1. **Swappable providers.** LLM and Git host are both behind narrow
   interfaces — a 400-engineer org will want to A/B different models and
   may migrate hosts. We don't want that to be a rewrite.
2. **Explicit dependencies.** Workflow functions take their collaborators
   (`llm`, `op`, `gh`) as arguments rather than importing singletons.
   That makes them trivial to test and trivial to compose.
3. **Idempotent re-runs.** A local SQLite DB records which stages have run
   against which work package. `--force` overrides. This matters because
   LLM calls cost money and nobody wants to re-spec the same ticket because
   cron ran twice.
4. **Human-in-the-loop by default.** Stage 3 opens PRs as *drafts*. Stage
   1 leaves a comment saying "AI-DLC drafted this — please review". No
   auto-merges, no auto-close.

## Data flow

```
┌────────────┐  idea   ┌──────────────┐  spec   ┌───────────────┐
│ OpenProject├────────▶│ idea_to_spec │────────▶│ spec_to_tasks │
│ WP #100    │         │  (Claude)    │         │   (Claude)    │
└────────────┘         └──────┬───────┘         └──────┬────────┘
                              │                        │
                              ▼                        ▼
                      patch description        create N child WPs
                      + transition status         under #100
                                                        │
                                                        ▼
                                                ┌───────────────┐   PR
                                                │ task_to_code  ├────────▶ GitHub
                                                │   (Claude)    │◀─(snap)─┤
                                                └───────┬───────┘         │
                                                        │                 │
                                                        ▼                 │
                                                  SQLite snapshot  ◀──────┘
                                                        │
                                                        ▼
                                                ┌────────────────┐
                                                │ status_updates │
                                                │ (cron, no LLM) │
                                                └────────────────┘
```

## Why OpenProject (not Jira Server)?

Jira Server was EOL'd in February 2024. Data Center replaces it but is
enterprise-priced (500-user minimum, ~$44K/year floor). OpenProject CE is
open-source, self-hostable via a single docker-compose file, and has a
HAL+JSON REST API that's arguably cleaner than Jira's. The feature set that
matters for AI-DLC — work packages, parent/child, statuses, types, and
machine-readable descriptions — maps directly.

## Why a hand-rolled GitHub client?

We use 6 endpoints. PyGithub and ghapi pull in large, eagerly-typed
surfaces. A hand-rolled client keeps the retry/error shape consistent with
`OpenProjectClient` and means contributors only have one style of HTTP
client to understand.

## State: SQLite over "remote-truth"

We considered making the agent stateless — recompute everything from OP +
GitHub on every tick. Rejected because:

- **Transition detection is cheaper with a snapshot.** Without a local
  snapshot, stage 4 would need to re-fetch every PR's check-runs on every
  run to decide if anything changed.
- **"Have we already run this?" is a cross-cutting concern.** Embedding it
  in OpenProject (via labels or custom fields) couples the agent to a
  specific OP configuration.

The DB lives at `.aidlc/state.db` by default. Treat it as disposable —
losing it means the agent re-runs stages. The *code* state in GitHub and
the *spec* state in OpenProject are the sources of truth.

## What's deliberately missing

- **Webhooks.** Polling is simpler to reason about for a POC. Swap in
  webhooks when you productionise.
- **Multi-tenant.** The agent operates against one OP instance + one repo.
  Fine for a pilot squad; not for an org-wide rollout.
- **Rate-limit budgeting.** The retry/backoff handles transient rate
  limits but there's no global budget. A real deployment should track
  token spend per workflow run and cut off at a daily ceiling.
- **Human approval gates.** All stages execute immediately. A safer
  design would post the proposed spec/tasks/code as draft comments first
  and only commit on explicit approval.
