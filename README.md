# Frontier World Skills

Reusable, production-oriented Codex Skills maintained by Frontier World in the [FrontierOpen](https://github.com/FrontierOpen) GitHub organization.

This repository currently contains `frontier-signals`, the editorial workflow for Frontier World’s AI news column. It separates internal research from public copy, keeps one canonical article record, validates editorial and release gates, and produces review-ready WeChat deliverables.

## Available skill

| Skill | Description | Status |
| --- | --- | --- |
| [`frontier-signals`](./frontier-signals/) | Researches, writes, illustrates, validates, and prepares sourced Chinese WeChat articles about AI models, agents, companies, founders, research, and policy. | Active |

## Frontier Signals

`frontier-signals` provides an end-to-end editorial workflow:

- discover and evaluate current AI news;
- build a source and claim ledger before drafting;
- write bulletin, report, or profile articles in the Frontier Signals brand-account voice;
- keep full research notes separate from concise reader-facing copy;
- manage image provenance, rights, purpose, and accessibility metadata;
- validate article length, claims, sources, media, and publication state;
- render WeChat-ready inline HTML and Markdown;
- create a deterministic 900×383 WeChat cover;
- recheck volatile product states such as availability, pricing, regions, account tiers, and Preview or Stable status;
- verify local previews at 375 px and 677 px;
- require explicit authorization before saving a remote draft or publishing.

The canonical article source is `signal.json`. Channel artifacts are rendered from it rather than edited independently. Supporting evidence and the complete fact ledger remain in `signal.json` and `source-notes.md`.

By default, the workflow stops at a local review package:

```text
signal.json
source-notes.md
wechat.html
wechat.md
wechat-cover.png
images/
release.json
```

## Repository structure

```text
skills/
├── README.md
└── frontier-signals/
    ├── SKILL.md       # Editorial workflow, rules, and release gates
    ├── agents/        # Agent-facing metadata
    ├── assets/        # Brand assets, templates, and structural examples
    ├── references/    # Research, writing, visual, and WeChat release guidance
    ├── scripts/       # Validators and deterministic renderers
    └── tests/         # Validation, rendering, and cover regression tests
```

## Installation

Clone the repository:

```bash
git clone https://github.com/FrontierOpen/skills.git
cd skills
```

Copy or link the skill directory into the skills directory used by your Codex environment:

```bash
ln -s /path/to/skills/frontier-signals /path/to/codex-home/skills/frontier-signals
```

Read [`frontier-signals/SKILL.md`](./frontier-signals/SKILL.md) before use. Files under `assets/` are templates and structural fixtures, not current production data.

## Usage

From the `frontier-signals` directory:

```bash
python3 scripts/validate_signal.py /path/to/signal.json

python3 scripts/render_wechat.py \
  /path/to/signal.json \
  --html /path/to/wechat.html \
  --markdown /path/to/wechat.md

python3 scripts/render_cover.py \
  /path/to/signal.json \
  --output /path/to/wechat-cover.png

python3 scripts/validate_signal.py \
  /path/to/signal.json \
  --require-media
```

Python 3 is required. Cover rendering and cover tests require Pillow.

## Validation

Validate the Skill package and run the regression suite before opening a pull request:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py frontier-signals
python3 -m unittest discover -s frontier-signals/tests -p 'test_*.py' -v
```

For strict article validation:

```bash
python3 frontier-signals/scripts/validate_signal.py \
  /path/to/signal.json \
  --strict \
  --require-media
```

## Development standards

- Keep each skill self-contained and independently understandable.
- Keep deterministic validation and rendering logic in scripts.
- Document editorial rules, external services, permissions, and failure behavior in `references/`.
- Treat example inputs as structural fixtures, never as current production facts.
- Preserve the separation between internal research records and public copy.
- Do not bypass validation or publication approval gates.
- Do not commit credentials, authentication state, generated working files, operating-system metadata, or private user data.

## Contributing

Issues and pull requests are welcome. Contributions should include:

1. A focused use case and clear trigger conditions.
2. Updated instructions and references for changed behavior.
3. Regression tests for deterministic scripts.
4. Explicit permission and failure rules for external integrations.
5. No secrets, personal information, or environment-specific runtime data.

## Security

Never commit API keys, access tokens, browser sessions, private documents, or production data. Remote draft creation and publication require an explicitly authorized account session and an approved article version. If a credential is exposed, revoke it immediately and report the incident through the repository’s security channel rather than a public issue.
