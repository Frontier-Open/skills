# Frontier Signals Agent Desk

Agent Desk 把选题发现、材料核实和独立审稿做成有界并行编辑部。它只写本地候选、研究记录和 `article.md`，永远不持有微信或 Cloudflare 凭据，也不执行外部发布。

## 角色

- **Chief Editor**：根 Agent。确定时间窗、去重、打分、选择唯一主选题，合并最终稿。
- **Scout**：按信源线并行发现候选，只提交 pitch card 和原始入口，不写正文。
- **Researcher**：围绕已选事件分别核实一手状态、独立背景、反方证据和读者影响路径，写入 `source-notes.md` 草案。
- **Reviewer**：不参与初稿写作，独立检查标题承诺、claim 归属、证据链、读者影响、图片权利和语气。
- **Visual Researcher**：只在事实框架稳定后找证据图、核权利和移动端可读性。

## 硬边界

- 一轮最多 3 个并行 worker；Chief Editor 始终保留一个执行槽。
- 候选最多 5 个，只选择 1 个进入写作；不得按文章数量补齐。
- 每项子任务最多重试 1 次；同一阻塞再次出现就记录失败，不无限循环。
- Scout 和 Researcher 只读外部网页；不得取得微信、Cloudflare、邮箱或社交账号写权限。
- Reviewer 只能提出修改或更新本地稿件，不能把“审稿通过”解释为渠道授权。
- 定时自动化只能完成雷达和候选包；不得自动创建微信草稿或部署网站。

## 一轮运行

1. 用 `scripts/init_desk_run.py` 创建 `desk-run.json`，记录时区、窗口、并发、候选上限和重试上限。
2. 并行启动最多三个 Scout，覆盖 source radar 的五条线；每个 Scout 返回结构化 pitch cards、失败入口和检查时间。
3. Chief Editor 去重并评分。没有合格候选时把状态写成 `no_publishable_signal`，停止本轮。
4. 只对排名第一的候选并行启动 Researcher：一手状态、独立证据与反方、读者影响与社区问题各一项。
5. Chief Editor 合并到 `source-notes.md`，满足五件材料、读者相关性和证据门槛后才写 `article.md`。
6. 独立 Reviewer 检查正文与 frontmatter；Visual Researcher 检查媒体。修改后只再做一轮复核。
7. 运行 `article:prepare`。渲染成功只把 desk run 标为 `local_package_ready`，发布授权仍由 [markdown-release.md](markdown-release.md) 管理。

## `desk-run.json`

运行记录不是第二份正文。至少记录：

~~~text
run_id / timezone / started_at / window_start / window_end
max_workers / max_candidates / max_retries / status
scout_tasks / candidates / selected_candidate_id
research_tasks / reviewer / failures / finished_at
~~~

每个任务记录 role、scope、status、attempts、started_at、finished_at 和 output_path。所有 outward actions 保持空数组；如果出现微信或网站动作，说明角色边界已经被破坏，必须停止。
