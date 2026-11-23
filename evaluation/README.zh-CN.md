# 基线模型评测

[English](README.md) | **简体中文**

基线使用仓库根目录的[单关入口](../run.py)。要查看某关的动作上限、Recall 额度和 Tip 触发阈值，可运行：

```bash
python run.py --level L2-01
```

这条命令不启动模拟器，也不调用模型。正式评测请参考 [API key 使用示例](../README.zh-CN.md#模型评测)，指定一个关卡和自己账号可用的模型。只有加上 `--live` 才会向供应商发送请求。基线不使用订阅登录、后台队列或批量派单。

要评测记忆代理方法，请使用单独的 [CoordMem 入口](../coordmem/README.zh-CN.md)。基线的通关结果与动作数见[评测结果说明](../README.zh-CN.md#评测结果)。
