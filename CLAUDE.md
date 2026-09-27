# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read first

`PROJECT_NOTES.md` (Russian) is the running working memory between sessions: author's decisions, incidents, what is deployed, open tasks. Read its newest sections (bottom of file) before doing anything, and append to it when something is decided. Work branch: `claude/session-continuation-2r2ln2`.

## What this repo is

Production pipeline for a solo lofi-jazz YouTube channel (first channel: "Jazzt a Pengui"). Three independent systems:

1. **n8n workflows** (`workflows/*.json`) running on the author's n8n server. Editing the files changes nothing live — the author re-imports them manually.
   - `10_Единый_редактор.json` — main Telegram bot: one "Editor" (OpenAI `/v1/responses`, one conversation per project) drives picture → text block (8 numbered items) → final summary → approval → sheet. **Generated — never edit by hand** (see below).
   - `04_Video.json` — takes approved project + tracks zip, calls the assembler, uploads to YouTube (timecodes, tags).
   - `11_Календарь.json` — calendar of episode occasions.
   - `00`–`03`, `99` — older workflows; `00` and `10` share one Telegram bot webhook, so only one of them may be active.
2. **Assembler** (`assembler/app.py`) — Flask + ffmpeg service on Coolify: `/assemble`, `/trackinfo`, `/thumbnail/<id>`, `/health`. Bump `ASSEMBLER_VERSION` on every change; `/health` reports it. The author deploys it herself (`wget -O /app/app.py <raw url of this branch>` then Restart, not Deploy — `/app` is persistent storage untouched by Deploy).
3. **Google Sheet** `1yEolX-8NV7NInu3OwCoxo2KSSNMny9dk-AVrpKdyNEs` — the control panel. `Templates` sheet holds per-channel settings/prompts (column prefixes: 🖋 text/Editor, 🎨 picture, 🎬 assembler); one sheet per channel holds project rows (`sys_*`, `ai_*`, `fx_*` columns; `sys_EditorState` is JSON state). `table_drafts/` holds drafts of long cells for the author to paste.

## Core rule: code is mechanics only

Everything creative or channel-specific (tone, style, prompts, character, reference images and their roles, image model, sound/overlay numbers) lives in the Sheet, never in code. No channel names or content ("Pengui" etc.) in code. Code changes to workflows or the assembler only after the author's explicit "да"; show a summary/diff first.

## Generator for workflow 10

`tools/gen10/gen.py` builds `workflows/10_Единый_редактор.json` from `tools/gen10/js/*.js` (each JS file is the body of one n8n Code node; `lib_state.js` is prepended to some). Drawing nodes are copied from `workflows/01_Художник.json`. Workflow: edit JS/gen.py → regenerate → check → test.

```bash
python3 tools/gen10/gen.py      # regenerate workflows/10_Единый_редактор.json
python3 tools/gen10/check.py    # node syntax, $('...') refs, connections, fan-out, orphans, credentials; expect "problems: 0"
node tools/gen10/test.js        # scenario tests for workflow 10 (Code nodes run via harness.js)
node tools/gen10/test04.js      # tests for Code nodes inside workflows/04_Video.json
python3 -c "import ast;ast.parse(open('assembler/app.py').read())"   # quick assembler syntax check
```

There is no single-test runner: tests are sequential `assert` blocks in one script. `harness.js` `run(nodeName, {nodes, input})` executes a Code node with a mocked `$('Node')`; use it to try one node in isolation.

Key flow in workflow 10: `Разбираем ответ редактора` (parse.js) → if the Editor called `commission_story`/sent `storyBrief`, a separate Writer writes the English description (`pisatel_zadanie.js`), it is translated for the author (`pisatel_perevod.js`), then merged in `Парсим ответ редактора` (pisatel_itog.js), which all downstream nodes read. The Editor performs only one tool call per turn.

## Other

- `tools/colab/suno_clean.ipynb` — Google Colab notebook denoising Suno tracks with Mel-RoFormer (audio-separator) before assembly.
- `compose_backup/` — n8n docker-compose backups (DNS fix for OpenAI).
- Communicate with the author in Russian, plainly, with copy-paste-ready text in code blocks; no model identifiers in commits.
