# Browser levels / 网页关卡

The 94 Playtest rooms follow L1 → H1 → L2 → H2. Levels 1–39 are L1 (easy); Levels 40–50 are H1 (medium-a); Levels 51–72 are L2 (medium-b); Levels 73–94 are H2 (hard). Level 38 retains the stage-manager office. This folder still uses internal indices 1–44 for L2 and H2 assets; H1 loads from playtest/hall. These display numbers do not change benchmark IDs or the evaluation API.

网页用第一人称视角展示程序生成的关卡；不是模拟器发送给模型的实际画面。网页版使用原关卡的 Python 机关逻辑和程序几何，浏览器负责 WebGL 渲染、近距离拾取、走位和快捷栏。网页 Level 68（此资源包内部第 18 关）的内页文字在网页副本中略向可见面偏移，避免与书架几何重叠。柜门展开时可能轻推玩家至相邻可站位置；这些显示与操控适配不会改写原始关卡。

The numbered scripts contain zipped Python modules for the corresponding rooms; engine-pack.js contains the shared rendering adapter, dependencies from the project, procedural textures and licensed font. The runtime is local to the browser. [Third-party notices](../python/THIRD_PARTY.md).
