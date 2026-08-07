# Claire Skills

玉婷工作流使用的本地 Codex Skills 统一放在这里。

```text
skills/
└── <skill-name>/
    ├── SKILL.md
    ├── agents/
    ├── scripts/
    ├── references/
    └── assets/
```

约定：

- 一个子目录只承载一个 Skill，目录名与 `SKILL.md` 中的 `name` 一致。
- 每个 Skill 自包含、独立测试；需要单独发布时，子目录可以拥有自己的 Git 仓库。
- 共用的用户资料或长期知识不复制进 Skill，保留在共享知识层。
- API 密钥、登录状态、Token、生成中间文件和每日运行数据不提交到 Git。
- 新 Skill 完成后，链接到 `~/.codex/skills/<skill-name>` 供 Codex 自动发现。

当前 Skill：

- `daily-tech-brief`：采集、筛选、核验、渲染并准备发送每日科技晨报。
