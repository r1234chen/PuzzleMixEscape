# PuzzleMixEscape

[English](README.md) | **简体中文**

**PuzzleMixEscape 是一个包含 94 个三维密室逃脱关卡的多模态模型评测基准。** 它考察模型能否在第一人称视角下主动寻找线索、理解空间关系，并通过一系列操作解开谜题。例如，在「维修储物间」（L2-01），模型需要移动视角清点散落的彩球，把观察结果与房间中的便签、工具箱和通风格栅联系起来。只有实际打开已解锁的出口门才算通关。

[关卡目录](level/index.json) · [环境安装](#环境安装) · [场景资产](assets/README.zh-CN.md) · [模型评测](#模型评测) · [基线指南](evaluation/README.zh-CN.md) · [CoordMem](#coordmem) · [评测结果](#评测结果)

## 关卡与评测协议

关卡沿**探索难度**和**谜题复杂度**两个维度分组。两个中等难度组强调不同能力：`medium-a` 要求模型在更大的空间范围内寻找和关联线索；`medium-b` 保持基础探索范围，但增加谜题的推理要求。

| 难度 | 关卡编号 | 探索 / 解谜 | 关卡数 | 动作上限 | 基线 Recall 额度 | Tip 触发阈值 |
|---|---|---|---:|---:|---:|---:|
| easy | [L1-01 至 L1-39](level/easy/) | 基础 / 基础 | 39 | 150 | 10 | 25 |
| medium-a | [H1-01 至 H1-11](level/medium-a/) | 增强 / 基础 | 11 | 200 | 20 | 50 |
| medium-b | [L2-01 至 L2-22](level/medium-b/) | 基础 / 增强 | 22 | 200 | 15 | 40 |
| hard | [H2-01 至 H2-22](level/hard/) | 增强 / 增强 | 22 | 250 | 25 | 60 |

每步决策时，基线模型可以看到 640 × 360 的第一人称图像、物品栏、笔记和最近 10 步交互。**Recall** 用于查阅更早的记录，单独计数，不消耗环境动作。**Tip** 在连续无进展的动作数达到表中阈值时附在动作反馈后，每局至多一次，不额外消耗动作或 Recall。拿到钥匙或解锁出口本身不算通关；出口门打开后不要求再走出去。

## 环境安装

本项目使用 **Python 3.11、OmniGibson 3.9.1 和 Isaac Sim 5.1**，需要兼容的 NVIDIA RTX GPU 和驱动。先按 [BEHAVIOR 官方安装指南](https://behavior.stanford.edu/getting_started/installation.html) 安装模拟器；如需复现本项目的环境，可使用[对应版本的模拟器源码](https://github.com/StanfordVL/BEHAVIOR-1K/tree/78980ee463b900226e48b956ae53a6f799ad8cc1)。

激活模拟器的 Python 环境后，在 **PuzzleMixEscape 仓库根目录**执行以下命令。这里和下文均以 `L2-01` 为例。

```bash
python -m pip install -r evaluation/requirements.txt
python setup_assets.py --level L2-01
```

安装脚本从官方来源获取资产，存放到 `assets/datasets/`。L2、H2 的房间由本仓库的代码生成，需要下载机器人资源；L1、H1 还需要 BEHAVIOR 的房屋与物体数据集，首次下载时按提示确认数据许可。已下载的资产可供其他关卡复用。

**验证安装（无需 API key）。** 以下命令会在 L2-01 的原生场景中执行参考解法，直到打开出口。该示例用于检查渲染和交互是否正常，不计为模型成绩。

```bash
python run.py --level L2-01 --standard
```

## 模型评测

每次运行评测一个关卡，由 `--level` 指定。下面以 OpenAI API 和 GPT-6-Astra 为例。在 PowerShell 7 中输入自己的 API key，然后运行评测：

```powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key" -MaskInput
python run.py --level L2-01 --provider openai_official --model gpt-6-astra --confirm-medium --live --out l2-01-gpt-6-astra
```

`--confirm-medium` 表示已确认所选模型支持中等推理强度；`--live` 才会向模型服务发送请求，可能产生费用。要评测其他关卡，请替换 `--level`，并为 `--out` 指定新的运行名；省略 `--out` 时自动使用时间戳。只想核对某关的配置和预算时，可运行 `python run.py --level H2-03`，不会启动模拟器或调用模型。

| 接口（`--provider`） | 密钥环境变量 | 模型设置 |
|---|---|---|
| `openai_official` | `OPENAI_API_KEY` | Responses API；图像输入，推理强度 `medium` |
| `openrouter` | `OPENROUTER_API_KEY` | 模型名使用 `provider/model`；推理强度 `medium`；需设置 `PUZZLEMIX_OPENROUTER_PROXY` |
| `dashscope` | `DASHSCOPE_API_KEY` | `qwen3.8-max`；启用思考，`thinking_budget=1024`，无需 `--confirm-medium` |

## CoordMem

CoordMem 每步先调用记忆代理，再调用解谜代理。`selective` 模式只把记忆代理为本步选中的记录交给解谜代理；`full` 模式提供全部未归档记录。两个代理使用相同的接口和模型，两种模式下解谜代理都**不提供独立 Recall**。动作上限、Tip 规则和通关条件与基线一致。

```powershell
python coordmem/run.py --level L2-01 --mode selective --provider openai_official --model gpt-6-astra --confirm-medium --live
```

将 `selective` 换成 `full` 即可切换模式。正常情况下，每个决策步会产生两次可能计费的模型请求。记忆记录的格式与输出文件见 [CoordMem 方法说明](coordmem/README.zh-CN.md)。

## 评测结果

上述 GPT-6-Astra 示例的结果保存在 `runs/l2-01-gpt-6-astra/episodes/L2-01/RESULT.json`。先看 `status` 判断评测是否正常结束，再看 `success` 判断是否通关、`actions` 查看实际动作数。正常耗尽预算但未通关，与接口或环境异常导致的中断，应分开统计。

同一目录还保留第一人称观测、模型交互和里程碑记录，便于分析模型在哪一步取得进展或停止推进。参考解法的验证结果单独写入 `FULL_STANDARD_RESULT.json`。

## 许可证

本项目的原创软件采用 [MIT 许可证](LICENSE)。第三方代码、数据和字体保留各自的许可与署名，见[第三方说明](THIRD_PARTY_NOTICES.zh-CN.md)。
