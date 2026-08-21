---
schema: frontier-signals/article@2
id: 2026-08-18/example-signal
date: 2026-08-18
slug: example-signal
format: report
title: 示例标题需要直接说明报道对象
description: 用一到两句交代事件、具体读者价值和 Frontier Signals 的判断。
thesis:
  core: 写下一句可以被未来事实推翻的核心判断。
  boundary: 写清判断成立的条件、当前未知和会改变判断的观察指标。
cover: wechat-cover.png
hero: og.png
wechat:
  author: ""
  digest: 用不超过 120 个字符概括文章，不重复标题。
  topics: [AI, 示例主体]
  comments:
    enabled: true
    fans_only: false
media:
  - path: wechat-cover.png
    alt: Frontier Signals 示例封面
    credit: Frontier World
    rights: owned
    purpose: cover
    generated: false
  - path: og.png
    alt: Frontier Signals 示例网站头图
    credit: Frontier World
    rights: owned
    purpose: hero
    generated: false
  - path: images/evidence.png
    alt: 支撑正文第一项关键事实的官方截图
    caption: 图注只补充读图条件或结果。
    credit: 官方发布方
    rights: official
    purpose: evidence
    generated: false
    show_caption: true
sources:
  - id: S1
    kind: primary
    title: 官方材料标题
    publisher: 官方发布方
    url: https://example.com/source
    published_at: 2026-08-18T09:00:00+08:00
    checked_at: 2026-08-18T12:00:00+08:00
claims:
  - id: C1
    kind: fact
    statement: 这里记录正文关键事实的中性表述。
    source_ids: [S1]
    test_run_ids: []
    confidence: high
test_runs: []
---
# 示例标题需要直接说明报道对象

第一屏先交代发生了什么、影响哪类读者，以及为什么今天值得知道。

再用已经核实的事实给出一句有边界的编辑判断。正文只在这份 Markdown 中维护。

## 发生了什么

用具体动作、时间、数字和主体还原事件。需要强调时，每段只保留一处 **真正帮助扫读的重点**。

![支撑正文第一项关键事实的官方截图](images/evidence.png "图注只补充读图条件或结果。")

## 机制与限制

解释产品、技术或商业机制，同时写清反方解释、未知和现实限制。

## 影响会落到谁身上

说明具体角色、影响路径、发生条件和大致时间范围。

## 延伸阅读

- [官方材料标题](https://example.com/source)
