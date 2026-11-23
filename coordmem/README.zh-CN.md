# CoordMem

[English](README.md) | **简体中文**

每个环境动作之前，CoordMem 先调用记忆代理，再调用解谜代理。两者使用同一个多模态模型和同一个 API key，但分别发送请求。记忆代理根据已交付的第一人称图像、物品栏和上一步反馈，更新四类记录：物体与位置、线索、待办事项和已做的尝试。解谜代理接收记忆记录、最近 10 步交互和当前画面，输出一个动作。

| 模式 | 解谜代理收到什么 |
|---|---|
| `selective`（默认） | 仅接收记忆代理通过 `push_ids` 为本步选中的有效记录，以及对应的线索图像。 |
| `full` | 接收全部未归档记录及其线索图像。 |

[基线](../evaluation/README.zh-CN.md)不加载 CoordMem。两种 CoordMem 模式下，解谜代理都**没有独立的 Recall 或笔记编辑动作**。更新记忆不消耗环境动作；动作上限、Tip 规则、评分和打开出口门的通关条件均保持不变。

## 单关评测

按[安装说明](../README.zh-CN.md#环境安装)安装原生环境和所选关卡的资产。以下命令均在仓库根目录执行。只检查配置时不需要 API key：

```powershell
python coordmem/run.py --level L2-01 --mode selective
```

正式评测时，在 PowerShell 7 中输入自己的 key，并使用账号实际可用的模型：

```powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key" -MaskInput
python coordmem/run.py --level L2-01 --mode selective --provider openai_official --model gpt-6-astra --confirm-medium --live
```

将参数改为 `--mode full` 即可提供全部有效记录。正常每个决策步产生**两次可能计费的请求**，每个代理一次。接口错误会停止运行，不编造记忆或动作。

| 接口 | 密钥环境变量 | 设置 |
|---|---|---|
| `openai_official` | `OPENAI_API_KEY` | 显式使用 `medium` 推理强度。 |
| `openrouter` | `OPENROUTER_API_KEY` | 显式使用 `medium`；另设 `PUZZLEMIX_OPENROUTER_PROXY`。 |
| `dashscope` | `DASHSCOPE_API_KEY` | `qwen3.8-max`，`thinking_budget=1024`；无需 `--confirm-medium`。 |

两个代理均不读取订阅登录凭据，也不回退到其他认证方式。

## 输出文件

每次只评测一个关卡，结果保存在 `runs/<运行名>/episodes/<关卡ID>/`。

| 输出 | 内容 |
|---|---|
| `RESULT.json` | 环境结果与动作数。 |
| `API_CALLS.json` | 解谜代理的响应记录，不是两代理的总调用量。 |
| `MEMORY_API_CALLS.json` | 记忆代理的响应记录。 |
| `COORDMEM_USAGE.json` | 两个代理各自已完成的响应数及合计。 |
| `MEMORY_STATE.json` | 记忆记录及其当前状态。 |
| `dual_agent/` | 逐步输入、响应及记忆更新。 |
| `PUBLIC_SUMMARY.json` | 当前模式及独立 Recall 的可用性。两种模式均不提供独立 Recall，不列额度或剩余次数；若有 `recalls` 字段，它表示已执行的次数。 |

这些是本地实验记录，不随源码发布。
