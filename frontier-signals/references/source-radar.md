# Frontier Signals 选题信源雷达

这份清单用于发现候选事件和有明确用途的开源实操题，不替代事实核验。只追踪 AI、大模型、Agent，以及直接改变其能力、成本、部署、公司竞争、资本配置或治理的事件与工具。

## 导航

- [范围过滤](#范围过滤)
- [每轮最低扫描](#每轮最低扫描)
- [来源角色](#来源角色)
- [读者相关性门槛](#读者相关性门槛)
- [日常雷达与中文议程](#日常雷达与中文议程)
- [中英文社交媒体与社区](#中英文社交媒体与社区)
- [实验室与产品一手源](#实验室与产品一手源)
- [研究、开源与开发者生态](#研究开源与开发者生态)
- [商业、资本与公司动作](#商业资本与公司动作)
- [监管、政策与安全](#监管政策与安全)
- [候选池与去重](#候选池与去重)

## 范围过滤

纳入：

- 基础模型、多模态模型、推理模型、模型安全与评测；
- Agent 产品、协议、运行时、工具调用、记忆、权限与人工接管；
- 训练与推理基础设施、开发工具和开源项目，但必须能说明它们怎样改变模型或 Agent，或替哪类读者解决一个具体问题；
- AI 公司与创始人的融资、并购、IPO、人事、组织和商业动作；
- 直接约束生成式 AI、模型提供方、内容标记、版权、数据或算力的政策与判决；
- 已接近实际使用、或正在被传播成超过证据结论的研究。

排除：

- 只在标题或发布稿里顺带出现 AI 的普通科技、消费电子和企业服务新闻；
- 与模型或 Agent 没有直接关系的机器人、芯片、自动驾驶、Web3 和泛投资事件；
- 没有新事实的观点汇编、榜单搬运、融资名单和社交平台口水战；
- 只有预告、倒计时、无署名或无编辑责任的匿名爆料，以及无法回到原始材料的说法。有署名、有编辑责任的媒体匿名信源报道按“抢先报道”处理，不在此排除。

## 每轮最低扫描

1. 查看[投资界 AI 频道](https://www.pedaily.cn/i-ai/)与中文产业媒体的最新内容，补公司、融资、并购、IPO、创始人和中文市场议程。
2. 查看实验室官方发布、产品文档、模型仓库与 Hugging Face，确认模型、产品和接口的一手更新。
3. 查看 arXiv、GitHub Releases、Hugging Face Papers 与开发者生态，补研究、开源项目和真实工程变化。
4. 查看 Bloomberg、Reuters、Financial Times、TechCrunch 等独立商业媒体与监管机构，补抢先报道、组织、资本、法律、政策和争议边界。
5. 至少查看一个中文社交或内容社区入口，以及一个英文社交或开发者社区入口，识别当天正在升温的话题、真实争议、读者关心的问题和值得实操的开源工具。

候选少于三个，或一半以上都是模型发布、跑分或开发工具时，把时间窗扩到 72 小时，并优先补扫公司与资本、政策与安全、真实产品影响。扩展后仍没有合格事件就不发。

原始材料在最近 7 天内、过去 24 小时才在社区形成新讨论时，可以进入 `community-driven` 候选池。记录 `original_published_at` 与 `discussion_started_at`，正文按原始日期交代事件。七天以前的新闻材料只有出现新版本、实测、政策动作、正式投票或其他新事实时才重新进入候选池。`open-source-practical` 候选不要求项目刚发布，但要有当前可用版本、可复现路径和现实读者需求；项目最后维护时间、release 与 commit 必须如实写入内部材料。

为每条扫描线记录成功入口、失败入口、检查时间和覆盖窗口。官方主页遇到 403、超时或无索引时，依次尝试官方 changelog / release notes、产品文档或模型卡、官方 GitHub / Hugging Face、官方 RSS 或 sitemap。搜索摘要、网页镜像和媒体转载不能替代一手源；整条扫描线不可用时标记 `incomplete`，继续其他线，但不能据此声称该方向当天没有新闻。

## 来源角色

| 角色 | 可以证明什么 | 使用规则 |
| --- | --- | --- |
| 雷达 | 某件事正在被讨论，或出现了新线索 | 不能直接进入 claim ledger；先找到原文 |
| 一手 | 发布、版本、价格、接口、论文结果、公司动作、监管要求 | 保存原始链接、发布时间与检查时间；发布方自报仍保留归属 |
| 独立二手 | 背景、交叉核对、采访、利益关系与反方解释 | 高风险说法至少再找一条独立证据链 |
| 社区信号 | 当天是否有人持续讨论、争论集中在哪里、哪些限制最受关注 | 记录帖子、作者、时间和可见互动快照；只用于选题排序或证明某人说过什么 |
| 弱信号 | 社媒反应、聚合摘要、转载、未署名爆料 | 只用于找方向或证明某人说过什么 |

同一新闻稿被多家媒体转载仍是一条证据链。媒体引用同一匿名消息也只算一条。

独立媒体还承担“抢先报道”角色。署名调查、文件独家和有编辑责任的匿名信源报道可以进入候选池，不必等待官宣才开始研究。候选卡必须记录报道状态、信源类型、当事方是否回应，以及标题需要保留的归属词。转载数量不会把一条独家变成多条证据链，但会增加传播势能。

## 读者相关性门槛

社交热度只能说明有人正在讨论，不能说明 Frontier Signals 的读者会受到影响。每个候选先回答四件事：

1. 与哪一类目标读者有关；
2. 会改变他的哪项选择、成本、工作、机会或风险；
3. 影响通过什么事实路径发生，大约何时能感受到；
4. 哪件材料支撑这条路径。

读者相关性按 1–5 分单独评分。只有宽泛行业意义、没有具体角色与影响路径时最多 2 分；至少有一类目标读者、一个具体影响和材料支持的路径才可达到 3 分。低于 3 分的候选即使很热也不开稿，先缩小角度或放弃。影响不必覆盖所有读者，能准确服务一个目标群体比声称“所有人都会受影响”更有价值。

## 日常雷达与中文议程

| 来源 | 入口 | 主要用途 | 证据角色与注意事项 |
| --- | --- | --- | --- |
| 投资界 AI 频道 | https://www.pedaily.cn/i-ai/ | AI 融资、并购、IPO、公司、创始人与中文市场议程 | 雷达与二手来源；页面混合投资界自采及量子位、36氪、机器之心等转载，记录实际作者并回到原始信源 |
| 机器之心旧文与专题 | 通过站内搜索、搜索引擎或已有单篇链接定位 | 论文、研究者、模型与中文技术社区 | 当前主页不作为稳定新闻入口；只按事件补查，跑分和独家消息回到论文、官方仓库或当事人 |
| 量子位 | https://www.qbitai.com/ | 模型发布、产品、人物和传播热点 | 发现为主；标题情绪和发布方自测不继承 |
| 极客公园 | https://www.geekpark.net/ | 产品体验、开发工具、创始人与公司访谈 | 按事件补查；有真实实测或完整访谈时可作二手证据，转载继续追原文 |
| 晚点 LatePost | https://www.latepost.com/ | 中国 AI 公司、组织、资本与人物深度报道 | 独家与匿名消息保留媒体归属，并另找公司或独立证据 |
| 36氪 | https://36kr.com/ | 创业公司、融资、商业化与产品发布 | 按事件补查，只筛 AI 核心事件；融资金额和估值必须双链核验 |

### 投资界的专门规则

- 优先看 AI 频道中的融资、并购、IPO、公司组织、创始人访谈和产业数据，不因页面收录就纳入泛科技、机器人或科学奖项。
- 区分投资界原创、投资界综合和外部媒体转载。转载条目的独立证据身份属于原始媒体，不属于投资界再增加一条证据链。
- 对每条线索记录 `pedaily_url`、`pedaily_label`、`original_publisher`、`original_url`、`original_published_at`、`page_published_at`、`event_date`、`checked_at` 与 `source_chain_id`。`pedaily_label` 取 `original`、`composite` 或 `partner_reprint`；找不到原文时标记待追溯，不进入 claim ledger。投资界页面时间只表示该页面的发布时间，不能自动当作融资、交易或产品事件发生时间。
- `投资事件`、`上市事件`、`融资企业` 和产业图谱只用于发现对象与建立待核清单，不直接证明金额、估值或交易完成。
- 融资与并购至少回到公司、投资方、交易对手或监管文件中的一条一手确认，并补一条独立证据链。只有“投资界获悉”或单一匿名消息时，降低标题承诺或暂缓。

## 中英文社交媒体与社区

| 来源 | 主要用途 | 注意事项 |
| --- | --- | --- |
| 微信公众号与微信搜索 | 中文从业者议程、公司原发、授权转载和传播扩散 | 区分原发、授权刊载与转载；同一稿件的多次刊载只算一个信号 |
| 知乎、微博、即刻、Bilibili | 中文用户问题、产品体验、人物与争议 | 机构号可以证明其发布内容；点赞、收藏、转发和播放量只记录为有时间的热度快照 |
| X | 实验室、研究者、开发者和当事人的即时发布 | 官方账号只证明发布方说过什么；截图与转帖继续追原帖，公开指标随时会变 |
| Hacker News | 英文开发者兴趣、反方论点、技术限制和早期采用 | 记录条目链接、points、comments 与检查时间；分数和评论数不能证明产品有效 |
| Reddit | LocalLLaMA、MachineLearning、产品社区中的实测与问题 | 区分原作者、转帖和评论；删帖、投票波动与社区偏好会影响可见度 |
| Bluesky | 研究者、独立开发者和政策讨论 | 保存原帖与作者身份；转发链不能自动增加独立证据 |
| GitHub | Trending、Stars、Forks、Releases、Issues 与 Discussions | Release 和提交可以证明代码状态；Star、Fork 和 Issue 数不能替代安装量、稳定性或生产采用 |
| Hugging Face 与 ModelScope 社区 | 模型下载、收藏、讨论、量化与部署反馈 | 区分官方模型卡、第三方量化和社区复现；下载量不等于活跃用户或生产使用 |

先用全局热门页发现意外事件，再用候选关键词回查不同社区。每条社区信号记录：

~~~text
platform / post_url / author_or_account
posted_at / checked_at
visible_metrics
discussion_theme / objections
original_or_repost / related_source_chain_id
~~~

社区指标只能在同一平台、相近时间窗内比较，不能把 HN points、微博转发、知乎赞同、GitHub Stars 和视频播放量合成统一分数。评论密度、讨论是否来自不同参与者、有没有具体复现或反例，比一次截图里的绝对数字更重要。

重复转载、营销矩阵、机器人式转发和同一原帖的跨平台搬运只算一个传播链。某个入口需要登录、返回 403 或连接失败时标记 `incomplete`，继续其他入口；不能把访问失败写成“该平台没有讨论”。公开正文通常不展示内部热度数字，除非社区反应本身就是报道对象。

## 实验室与产品一手源

优先检查事件主体自己的 newsroom、文档更新、模型卡、GitHub Release 与 Hugging Face 组织页。下表是常用稳定入口，未列出的实验室仍按同样规则处理。

| 来源 | 入口 | 主要用途 |
| --- | --- | --- |
| OpenAI | https://openai.com/news/ | 模型、产品、研究、公司与安全公告 |
| OpenAI API Changelog | https://developers.openai.com/api/docs/changelog | API 模型、接口、版本和开放状态 |
| Anthropic | https://www.anthropic.com/news | Claude、研究、安全、政策与公司动态 |
| Claude Release Notes | https://platform.claude.com/docs/en/release-notes/overview | Claude API、模型上下线、功能和平台状态 |
| Google DeepMind | https://deepmind.google/discover/blog/ | Gemini、研究、模型能力与安全 |
| Gemini API Changelog | https://ai.google.dev/gemini-api/docs/changelog | Gemini 模型版本、Preview/Stable、配额和接口变化 |
| Meta AI | https://ai.meta.com/blog/ | Llama、开源研究与产品能力 |
| xAI | https://x.ai/news | Grok、产品和公司公告 |
| Microsoft AI | https://blogs.microsoft.com/ai/ | Copilot、Azure AI、合作与企业部署 |
| NVIDIA Developer Blog | https://developer.nvidia.com/blog/ | 训练、推理和 Agent 基础设施；只选直接影响模型成本或部署的更新 |
| DeepSeek | https://api-docs.deepseek.com/updates/，以及官方 GitHub 与 Hugging Face 组织页 | 模型、价格、接口、开源权重和运行时 |
| Qwen | https://qwen.ai/research；旧站 RSS：https://qwenlm.github.io/blog/index.xml | 模型发布、技术报告、开源权重与许可 |
| Z.ai / 智谱 | 官方公告、开发文档与模型仓库 | GLM 模型、工具、价格、安全与开放状态 |
| Moonshot AI / Kimi | 官方产品公告、平台文档与模型仓库 | Kimi、API、Agent 产品与开放模型 |
| MiniMax | 官方公告、开发文档与模型仓库 | 模型、产品、语音视频能力与商业化 |
| ByteDance Seed | https://seed.bytedance.com/en/blog/ | 模型、研究、Agent 与多模态发布 |
| 腾讯混元、百度文心、阶跃星辰 | 各自官方公告、开发文档与模型仓库 | 中国模型、产品、开源与企业部署 |

产品状态以当前文档、控制台或正式公告为准。社媒预告和演示只证明发布方展示过什么，不能证明已经全量开放。

## 研究、开源与开发者生态

| 来源 | 入口 | 主要用途 | 注意事项 |
| --- | --- | --- | --- |
| Hugging Face Blog | https://huggingface.co/blog | 开源模型、生态数据、工具与官方分析 | 把官方统计与作者观点分开 |
| Hugging Face Papers | https://huggingface.co/papers | 较新的 AI 论文与社区关注 | 社区热度不代表论文质量；回到论文原文 |
| Hugging Face Models | https://huggingface.co/models?sort=trending | 新权重、模型卡、许可与下载趋势 | 下载量、点赞和生产使用不是同一指标 |
| arXiv cs.AI | https://arxiv.org/list/cs.AI/recent | Agent、规划、推理与通用 AI 研究 | 预印本不是同行评审结论 |
| arXiv cs.CL | https://arxiv.org/list/cs.CL/recent | 大语言模型、语言、多模态与评测 | 检查版本、数据与代码是否公开 |
| arXiv cs.LG | https://arxiv.org/list/cs.LG/recent | 训练、优化、推理与机器学习方法 | 只有影响模型或 Agent 的研究进入候选池 |
| GitHub 官方组织与 Releases | 事件主体的官方组织页 | 代码、版本、许可证、提交与 issue | Star 只能证明关注；安装量、稳定性和采用率另找证据 |
| MLCommons | https://mlcommons.org/ | 标准化训练、推理与安全评测 | 先核配置、硬件、成本与可比性 |
| Artificial Analysis | https://artificialanalysis.ai/leaderboards/models；方法：https://artificialanalysis.ai/methodology | 独立能力、速度、延迟和价格比较 | 记录检查时间、测试配置、模型版本与方法；榜单会变化，不把综合分数写成绝对能力 |

### 开源项目选题路径

把开源候选分成三类：

- `open-source-release`：新项目、新版本、许可证或治理变化，按新闻窗口处理，可以写发布解读；
- `open-source-intro`：围绕当前可用项目解释它解决什么问题、适合谁和使用边界，不宣称编辑部已经运行；
- `open-source-practical`：围绕一个明确读者问题做介绍和实操，不强求当天发布，但必须真实安装和运行。

Frontier Signals 的开源实操优先关注三类真实工作：Agent 的编排、运行时、工具与人工接管；AI 剪辑、字幕、配音与视频生产；AI 图文、音频和多渠道内容生产。模型下载、硬件适配、通用运维等工具仍可进入新闻候选，但没有更强事件时，不优先占用实操栏目。

实操候选先回答：它替哪类读者省掉什么成本或步骤，现有方案为何不够，普通读者能否在合理时间与设备上复现。随后核对官方仓库与维护者、最新 release 或 commit、许可证、系统与硬件要求、依赖锁定、默认网络请求、遥测、密钥与权限、已知安全问题。README、GitHub Star、下载量和演示视频可以帮助发现项目，不能单独证明稳定性、易用性或生产采用。

没有完成干净环境安装、至少一个代表性任务和失败记录时，只能写项目介绍，不能使用“实测”“上手结果”或“值得部署”等结论。完整测试按 [hands-on-reporting.md](hands-on-reporting.md) 记录。

## 商业、资本与公司动作

| 来源 | 入口 | 主要用途 | 注意事项 |
| --- | --- | --- | --- |
| Reuters AI | https://www.reuters.com/technology/artificial-intelligence/ | 公司、监管、交易、诉讼与全球产业 | 独立二手；财务与交易数字继续回到文件或当事方 |
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/ | 创业公司、融资、产品和并购 | 融资消息分清已完成、目标规模和媒体消息 |
| Crunchbase AI | https://news.crunchbase.com/sections/ai/ | 全球私募融资、公司与投资趋势线索 | 雷达和二手来源；金额、估值与交易状态仍须一手确认和独立证据链 |
| Financial Times AI | https://www.ft.com/artificial-intelligence | 大公司、资本、政策与国际竞争 | 可完整访问时补查，只使用实际读到并能准确归属的部分 |
| Bloomberg AI / Technology | https://www.bloomberg.com/ai；https://www.bloomberg.com/technology | 公司、资本市场、算力、政策与抢先爆料 | 作为每日抢先报道入口；署名独家可直接启动研究，不必等待官宣。只使用实际读到的标题与正文，付费墙外的搜索摘要不能补全细节；匿名消息、交易状态和估值口径始终保留归属 |
| Ars Technica AI | https://arstechnica.com/ai/ | 模型、产品、安全、法律与技术背景 | 适合补限制和争议，不替代一手状态 |
| The Decoder | https://the-decoder.com/ | 模型、论文、产品和政策快讯 | 只作雷达；发现后回到论文、文档、公告或独立报道 |
| 公司 IR 与交易双方公告 | 对应公司投资者关系页 | 财报、并购、合作、收入与风险 | 区分合同、意向、目标和已经完成的交易 |
| SEC EDGAR | https://www.sec.gov/edgar/search/ | 美国上市、财报、重大交易和风险披露 | 记录申报主体、表格类型、期间和会计口径 |
| 港交所披露易 | https://www1.hkexnews.hk/ | 香港 IPO、公告、股权与交易文件 | 以正式文件为准，不用媒体估值替换申报口径 |

## 监管、政策与安全

| 来源 | 入口 | 主要用途 | 注意事项 |
| --- | --- | --- | --- |
| 欧盟委员会 AI | https://digital-strategy.ec.europa.eu/en/policies/artificial-intelligence；法规原文：https://eur-lex.europa.eu/eli/reg/2024/1689/oj | AI Act、实施指南、准则与执法状态 | 区分法律、指南、草案、征求意见与生效时间 |
| NIST AI | https://www.nist.gov/artificial-intelligence | 风险管理、评测、安全标准与美国政策 | 标准和自愿框架不能写成强制法律 |
| Federal Register AI 检索 | https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=%22artificial+intelligence%22 | 美国拟议规则、最终规则、行政文件与生效日期 | 以文件类型、发布机关和正式日期判断法律状态，不把搜索命中都视为约束模型的政策 |
| UK AI Security Institute | https://www.aisi.gov.uk/ | 前沿模型评测、安全研究与政府合作 | 发布方结论与原始评测条件一起写 |
| 国家网信办 | https://www.cac.gov.cn/ | 中国生成式 AI、算法、数据与内容治理 | 只取正式文件，核对发布日期、适用主体与实施状态 |
| 工业和信息化部 | https://www.miit.gov.cn/ | AI 产业政策、标准、算力与企业管理 | 泛产业政策只有直接影响模型或 Agent 时才写 |
| 法院判决与监管文件 | 对应法院、监管机关或官方公报 | 版权、竞争、隐私、内容责任与交易审批 | 媒体报道用来找案号，核心结论回到裁判或正式文件 |

## 候选池与去重

每个候选在内部记录：

~~~text
topic_bucket
candidate_mode
discovered_via
original_publisher_or_speaker
discovery_url / aggregator_label
original_url / original_published_at
first_party_sources_found
independent_sources_found
page_published_at / event_date / checked_at / source_chain_id
social_signals / discussion_started_at / social_checked_at
duplicate_or_revision
reader_segment
decision_cost_work_opportunity_or_risk
impact_path / impact_horizon
impact_supporting_source_ids
reader_relevance_score / evidence_quality_score
why_this_reader_cares_now
headline_hook / search_terms / share_reason
reporting_status / attribution_needed
repository_url / release_tag / commit_sha / license
reproducibility_question / required_environment / test_status
claims_to_verify / claims_rejected
~~~

同一事件的新标题、新转载或新封面不是新选题。出现实质更新时修改现有故事，记录新增事实和过时句子。候选池可以广，开稿门槛不降低：没有五件能组成过程的具体材料，读者相关性低于 3 分，或证据质量低于 3 分，就不写。
