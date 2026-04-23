# AI-DLC Proof of Concept

A working AI Development Lifecycle agent wired to **self-hosted OpenProject
Community Edition** (as a Jira / Aha! stand-in) and **GitHub**. The agent
demonstrates four stages end-to-end:

1. **Idea → Spec** — read a raw feature idea, draft an implementation-ready
   spec, and patch it back onto the work package.
2. **Spec → Tasks** — decompose a spec into child engineering tasks.
3. **Task → Code / PR** — generate a scaffold PR on a real GitHub repo and
   link it back to the OpenProject work package.
4. **Status Updates** — poll tracked PRs, transition tickets on merge, flag
   CI failures, leave summary comments.

This is a scaffold you can extend — not a production autonomous coding
agent. Stage 3 in particular produces review-ready starter PRs; wiring it to
a real codegen pipeline (Claude Code, Aider, etc.) is a natural next step.

## Quick start

```bash
# 1. Clone + configure
git clone <this repo> aidlc && cd aidlc
cp .env.example .env
$EDITOR .env          # fill in ANTHROPIC_API_KEY and (later) OPENPROJECT_API_KEY + GITHUB_TOKEN

# 2. Start OpenProject locally (takes 2-5 min on first boot)
make up
# Open http://localhost:8080, log in as admin/admin (OP forces a password change).
# Then: My Account -> Access tokens -> create an API token -> paste into .env as OPENPROJECT_API_KEY.

# 3. Install the agent
make dev              # installs with dev deps

# 4. Seed demo data
make seed

# 5. Verify connectivity
aidlc doctor

# 6. Drive a feature through the pipeline
aidlc spec 1234       # replace 1234 with one of the seeded WP IDs
aidlc decompose 1234
aidlc code 1235       # the first child task from decompose
aidlc watch           # poll once for PR/CI transitions (put on cron for continuous)
```

## What's inside

```
aidlc/
├── config.py               # pydantic-settings — all secrets/paths live here
├── cli.py                  # typer CLI (spec, decompose, code, watch, run-all, doctor)
├── db.py                   # sqlite persistence for run history + PR snapshots
├── logging.py              # structlog setup (JSON via AIDLC_LOG_JSON=1)
├── llm/
│   ├── base.py             # provider Protocol + extract_json helper
│   └── anthropic.py        # Anthropic adapter with retries
├── openproject/
│   ├── client.py           # thin HAL+JSON client
│   └── models.py           # flattened pydantic models
├── git_host/
│   └── github.py           # minimal REST client: branch, commit, PR, check-runs
├── workflows/              # one module per AI-DLC stage
└── prompts/                # externalised prompt templates (*.md)

docker-compose.yml          # OpenProject CE + Postgres + Memcached
.github/workflows/ci.yml    # lint + type-check + tests (matrix py3.11/3.12)
scripts/seed_openproject.py # create demo project + sample ideas
tests/                      # pytest suite using in-memory fakes
```

## Configuration

Every knob lives in `.env` (see `.env.example` for the full list). Notable
ones:

| Variable | Default | Notes |
|---|---|---|
| `OPENPROJECT_URL` | `http://localhost:8080` | Base URL of the OP instance. |
| `OPENPROJECT_API_KEY` | *(required)* | Generate in OP → My Account → Access tokens. |
| `OPENPROJECT_PROJECT` | `ai-dlc-demo` | Default project identifier the agent operates in. |
| `ANTHROPIC_API_KEY` | *(required)* | For the LLM provider. |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Override if you want a different model. |
| `GITHUB_TOKEN` | *(required for stage 3)* | Fine-grained PAT on the target repo with `contents:rw` + `pull-requests:rw`. |
| `GITHUB_REPO` | *(required for stage 3)* | `owner/repo` the agent should open PRs against. |
| `AIDLC_DB_PATH` | `.aidlc/state.db` | SQLite file for run history. |

## Testing

```bash
make test          # pytest only
make check         # ruff + mypy + pytest
```

Tests never hit the real OpenProject or GitHub — they use in-memory fakes
and `respx` for HTTP-level client coverage.

## Running it against a real GitHub repo

1. Create a throwaway fork of a small repo (or a scratch repo with a
   `main` branch and at least one commit).
2. Issue a fine-grained PAT scoped to *only that repo* with:
   - Contents: read & write
   - Pull requests: read & write
3. Set `GITHUB_TOKEN`, `GITHUB_REPO`, and `GITHUB_BASE_BRANCH` in `.env`.
4. Run `aidlc doctor` — it will verify the PAT can resolve `HEAD` on the
   base branch.
5. Run `aidlc code <task-wp-id>`.

PRs are opened as **drafts** so CI runs but no one pages reviewers.

## Extending

- **Swap the LLM provider**: add an adapter under `aidlc/llm/`, extend the
  `LLMProvider` enum in `config.py`, register it in `llm/__init__.py:get_llm`.
- **Swap the Git host**: add an adapter under `aidlc/git_host/` exposing the
  same surface as `GitHubClient` (branch ops, commit, PR, check-runs).
- **Plug in a real coding agent**: replace `workflows/task_to_code.py`'s
  `llm.complete` call with a subprocess that invokes Claude Code / Aider
  against a clone of the target repo.

## Known limitations

- Stage 3 writes files via the GitHub Contents API — fine for ≤ 10 small
  files per PR. For larger changes you'd switch to Git Trees API or a
  local clone + push.
- Stage 4 polls rather than subscribing to webhooks — acceptable for a POC,
  replace with webhooks for production.
- OpenProject status names are environment-specific; the agent tries a list
  of common names and logs a warning if none match. Customize in
  `workflows/idea_to_spec.py` and `workflows/status_updates.py`.
- The agent has no RBAC story — it impersonates whichever user the API keys
  belong to. For production, provision a dedicated service account in OP
  and a GitHub App in place of a PAT.

## Licence

MIT.
