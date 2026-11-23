# CoordMem

**English** | [简体中文](README.zh-CN.md)

Before each environment action, CoordMem calls a memory agent, then an action agent. They use the same multimodal model and API key but send separate requests. The memory agent uses the delivered first-person images, inventory, and feedback on the previous action to update four kinds of records: objects and locations, clues, pending tasks, and attempts. The action agent receives memory records, the last 10 interactions, and the current view, and returns one action.

| Mode | What the action agent receives |
|---|---|
| `selective` (default) | Only the active records the memory agent selects for this step via `push_ids`, with the corresponding clue images. |
| `full` | All records that have not been archived, with their clue images. |

The [baseline](../evaluation/README.md) does not load CoordMem. In both CoordMem modes, the action agent has **no independent Recall or note-editing action**. Memory updates do not consume environment actions. Action budgets, the Tip policy, scoring, and the exit-door success condition are unchanged.

## Evaluate one level

Follow the [setup instructions](../README.md#setup) to install the native environment and the assets for your level. Run all commands from the repository root. The following checks the configuration without an API key:

```powershell
python coordmem/run.py --level L2-01 --mode selective
```

To run the evaluation in PowerShell 7, enter your own key and use a model available to your account:

```powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key" -MaskInput
python coordmem/run.py --level L2-01 --mode selective --provider openai_official --model gpt-6-astra --confirm-medium --live
```

Switch to `--mode full` to pass all active records. A normal decision step makes **two potentially billable requests**, one per agent. An API error stops the run; the program does not fabricate memory or an action.

| Provider | API key | Settings |
|---|---|---|
| `openai_official` | `OPENAI_API_KEY` | Explicit `medium` reasoning effort. |
| `openrouter` | `OPENROUTER_API_KEY` | Explicit `medium`; also set `PUZZLEMIX_OPENROUTER_PROXY`. |
| `dashscope` | `DASHSCOPE_API_KEY` | `qwen3.8-max`, `thinking_budget=1024`; omit `--confirm-medium`. |

Neither agent reads subscription login credentials or falls back to a different authentication method.

## Output files

Each run evaluates one level. Its files are stored in `runs/<run-name>/episodes/<level-id>/`.

| Output | Contents |
|---|---|
| `RESULT.json` | Environment outcome and action count. |
| `API_CALLS.json` | Action-agent responses; this is not the total for both agents. |
| `MEMORY_API_CALLS.json` | Memory-agent responses. |
| `COORDMEM_USAGE.json` | Completed response counts for each agent and their combined total. |
| `MEMORY_STATE.json` | Memory records and their current state. |
| `dual_agent/` | Per-step inputs, responses, and memory updates. |
| `PUBLIC_SUMMARY.json` | Mode and independent Recall availability. Neither mode has a Recall quota or a remaining count. If present, `recalls` counts past actions, not an allowance. |

These are local run records, not files distributed with the source code.
