# 实测、开源软件实操、抢先体验与产品对比

只有编辑部真实操作过产品，而且过程本身构成证据时，才使用实测写法。拿到截图、看过别人的演示或读完官方文档不算实测。

## 开测前

先写清测试要回答的一个问题。不要为了让文章更热闹随手跑 Demo，也不要拿审美任务证明模型的全部能力。

在内部测试记录中保存：

~~~text
tested_at / access_scope / region / account_tier
product_version / model_version / application_or_harness
task / prompt_or_input / acceptance_criteria
tools / permissions / reasoning_mode / relevant_settings
run_count / duration / tokens / cost
result / failures / retries / manual_intervention
artifact_paths / comparison_conditions / limitations
~~~

把这些字段写进 `article.md` YAML frontmatter 的 `test_runs` 数组，每组测试使用 `T1`、`T2` 形式的 ID。`run_count` 与 `retries` 使用整数，`artifact_paths` 至少保留一个稿件目录内的相对文件路径；产品没有提供 token、成本或其他数据时明确写“未提供”，不能删掉字段。

实测结果进入 claim ledger 时，在对应 claim 添加 `test_run_ids`。编辑部亲自观察到的结果可以写成 `fact`，保留空的 `source_ids: []` 并关联 `test_run_ids`；引语仍必须关联公开 `source_ids`。公开来源与内部实测是两类证据，`test_runs` 不计入来源数量，也不会出现在文末“延伸阅读”。

测试产品、模型、Harness、工具版本或上下文不同，就不能写成同条件横向对比。无法控制变量时，把它写成多个独立体验，不排出总名次。

## 开源软件实操

开源稿先确定它是“项目介绍”还是“编辑部实操”。项目介绍可以解释定位、架构、许可证和适用人群，但不能借用他人的演示冒充上手结果。只有完成真实安装与运行，才进入实操写法。

开始运行前先读安装脚本、容器配置、依赖清单和默认权限。优先在一次性临时目录、容器或隔离环境中操作，不向未知项目提供真实账号、生产数据、个人目录或长期密钥；需要联网、执行远程脚本、提升权限或连接外部服务时，先说明风险并取得相应授权。

在 `source-notes.md` 额外记录：

~~~text
repository_url / owner_or_maintainer / license
release_tag / commit_sha / last_release_at / last_commit_at
os / architecture / cpu / memory / gpu
runtime / package_manager / dependency_lock
install_commands / start_commands / default_ports
network_calls / telemetry / secrets / filesystem_permissions
clean_install_result / known_issues / uninstall_or_cleanup
~~~

同时把可审计的运行条件映射进现有 `test_runs`：`product_version` 写 release 与 commit，`application_or_harness` 写仓库和启动方式，`tools` 写实际安装与运行命令，`permissions` 写网络、密钥和文件权限，`relevant_settings` 写运行时、依赖锁与硬件条件，`artifact_paths` 保存命令输出、截图或结果文件。不要只把这些信息写在正文里。

至少完成一次干净环境安装、一个与目标读者有关的代表性任务，并保存命令、版本、输入、输出、耗时、失败与人工修正。安装成功只证明这套环境能启动；没有重复任务、长期运行和真实负载时，不写“稳定”“生产可用”或“零门槛”。许可证、维护频率、Issue 数量和 Star 各自表达不同信息，不能互相替代。

公开步骤只保留读者复现所需的命令和条件。会写入系统目录、打开公网端口、发送数据、下载可执行文件或消耗付费 API 的步骤，在相邻位置说明影响；不要为了教程流畅省略安全与成本前提。

## 证据边界

- 一次成功只证明这次任务成功，一次失败也不证明产品普遍失败；
- 视觉上“更好看”“更沉浸”属于编辑判断，说明评价标准，不伪装成客观性能；
- 发布方提供的内测环境与公开版本分开记录；
- 抢先体验必须写明 Preview、Beta、灰度、账号档位与观察时间；
- 对照测试保留完全相同的输入、验收条件和运行限制；
- 主动保留失败、超时、兼容问题和人工接管，不只展示最好的一次；
- 没有重复运行时，不写成功率、稳定性或“显著提升”；
- 测试日志、完整提示词和原始产物保存在内部材料，公开稿只展示理解结论所需的部分。

实测结论进入 claim ledger 时，写清它只适用于哪次环境与任务。产品官网或模型文档可以证明版本和功能，不能替编辑部证明一次本地运行结果。

## 公开写法

正文先说明为什么做这项测试，再给必要条件、结果和失败点。测试过程按读者理解结论所需的顺序写，不逐步复述操作日志。

可以使用“我们”，但只描述真实动作：

- `我们在 ZCode 中连续运行了三次同一任务`；
- `第二次在工具调用阶段超时`；
- `三次都需要人工确认文件写入`。

不用“我们先来看看”“我们都知道”“我们更关心的是”制造陪读感。没有编辑部实测时回到品牌官号的直接陈述。

结论先说这次测试看见了什么，再说明它不能证明什么。不要从一个游戏、一个网页或一张截图推导模型的总体排名。

## 图片与产物

每项重要结果尽量保留可核验产物。截图要能看出产品、版本、任务状态或结果，不只展示漂亮画面。

图片紧跟对应结论。必要时公开一句简短图注，交代测试条件、分组或图中需要注意的结果；图注不写来源播报，不重复上一段，也不替正文下新的大结论。
