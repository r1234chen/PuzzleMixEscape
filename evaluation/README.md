# Baseline model evaluation

**English** | [简体中文](README.zh-CN.md)

The baseline uses the [single-level entry point](../run.py) at the repository root. To inspect a level's action budget, Recall quota, and Tip threshold without starting the simulator or calling a model, run:

```bash
python run.py --level L2-01
```

For an actual evaluation, follow the [API-key example](../README.md#model-evaluation). Specify one level and a model available to your account. Only `--live` sends requests to the provider. The baseline does not use a subscription login, a background queue, or a batch scheduler.

For the memory-agent method, use the separate [CoordMem entry point](../coordmem/README.md). For the baseline outcome and action count, see [Results](../README.md#results).
