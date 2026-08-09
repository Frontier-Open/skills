# Frontier Open Skills

Reusable, production-oriented Codex Skills maintained by [Frontier Open](https://github.com/Frontier-Open).

This repository contains self-contained skill packages for repeatable research, content, publishing, and automation workflows. Each skill combines operating instructions with the scripts, references, and assets required to run and validate it.

## Available skills

| Skill | Description | Status |
| --- | --- | --- |
| [`daily-tech-brief`](./daily-tech-brief/) | Collects, curates, verifies, renders, archives, and prepares delivery of a sourced daily technology briefing. | Active |

## Repository structure

```text
skills/
└── <skill-name>/
    ├── SKILL.md       # Skill definition and workflow
    ├── agents/        # Agent-facing metadata
    ├── scripts/       # Deterministic automation and tests
    ├── references/    # Policies, schemas, and integration notes
    └── assets/        # Templates and example inputs
```

Every top-level skill directory is designed to remain independently understandable, testable, and reusable.

## Installation

Clone the repository:

```bash
git clone https://github.com/Frontier-Open/skills.git
cd skills
```

Install a skill by copying or linking its directory into the skills directory used by your Codex environment. For example:

```bash
ln -s /path/to/skills/daily-tech-brief /path/to/codex-home/skills/daily-tech-brief
```

Open the selected skill's `SKILL.md` for its prerequisites, workflow, and validation commands.

## Development standards

- Keep one skill per top-level directory and match the directory name to the `name` field in `SKILL.md`.
- Make each skill self-contained, deterministic where possible, and independently testable.
- Keep reusable logic in scripts instead of embedding large command sequences in instructions.
- Document external services, schemas, safety constraints, and failure behavior in `references/`.
- Include example inputs only as structural fixtures; never present sample data as current production data.
- Do not commit credentials, authentication state, generated working files, or private user data.

## Validation

Run the checks defined by the individual skill before opening a pull request. For `daily-tech-brief`:

```bash
cd daily-tech-brief
npm test
```

## Contributing

Issues and pull requests are welcome. A contribution should include:

1. A focused use case and clear trigger conditions.
2. A complete `SKILL.md` with explicit inputs, outputs, and failure rules.
3. Tests for deterministic scripts and validation for generated artifacts.
4. Documentation for required permissions and external integrations.
5. No secrets, personal information, or environment-specific runtime data.

Please keep changes scoped to one skill whenever possible.

## Security

Never commit API keys, access tokens, browser sessions, private documents, or production data. If a credential is exposed, revoke it immediately and report the incident through the repository's security channel rather than a public issue.
