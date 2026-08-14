# AIHOT 热点发现

## 用途

AIHOT 是 Frontier Signals 的内部选题雷达。它帮助发现当前热点、聚合相关报道和追踪事件更新。最终文章仍回到第三方原文、官方资料、论文和独立报道核验。

使用前读取当前环境中 aihot Skill 的完整 SKILL.md，服从它的 API、重试、时间轴和输出规则，不在这里复制可能变化的接口细节。

## 默认查询

一轮选题使用两个入口：

1. 当前热点榜，确认正在形成讨论的事件；
2. 过去 24 小时精选，发现还未进入热点榜但证据较强的新发布。

用户给出公司、模型或主题时，使用 aihot 的关键词查询。精选池返回空集时，按 aihot Skill 规则用同样参数查询全量池，并标记“未进入精选”。

热点已有 story 链接时，再读取对应事件 API，查看：

- 最早与最新报道时间；
- 官方来源是否已经出现；
- 新闻在传播中增加了哪些说法；
- 摘要里是否存在互相冲突的数字；
- 哪些内容只有单一公众号或社媒来源。

不要猜 story ID，也不要抓取 AIHOT 网页代替 API。

## 编辑使用

在内部 pitch card 记录：

~~~text
aihot_checked_at
hot_rank_if_any
aihot_item_or_story_url
first_party_sources_found
claims_to_verify
claims_rejected
~~~

排行只用于安排研究优先级。不要把第几名、来源数或 signal 数写成行业影响力证据。

从 AIHOT 找到原文以后，直接打开原文建立证据条目。AIHOT 的标题、summary、digest、reason 与第三方转载都不能直接进入 claim ledger。

## 许可与公开使用

AIHOT 的匿名访问不等于公开商业再分发许可。Frontier Signals 默认只把 AIHOT 用于组织内部的新闻发现：

- 不在公开文章里批量转载 AIHOT 标题、摘要、日报或事件综述；
- 不把 AIHOT 数据做成公开镜像、付费答案、数据产品或训练集；
- 不把 AIHOT attribution 当成商业授权；
- 公开文章引用第三方原文，并单独处理图片和文字版权。

如果团队希望在公众号中直接转载或长期展示 AIHOT 数据，先按 aihot Skill 指向的服务条款取得书面授权，再按授权范围使用。

## 失败降级

AIHOT 请求失败时按 aihot Skill 的有界重试规则处理。失败不意味着当天没有新闻，也不能切换到其它来源后声称结果来自 AIHOT。

记录“AIHOT 暂不可用”，随后可以继续查看官方更新页和已批准的独立新闻源。文章里无需提到这次内部采集失败。
