# 耳机少年 / Headphone Boy

![耳机少年九种动作预览](demo.gif)

黑发、白耳机、宽松卫衣的 Q 版少年。本项目最初完成的桌宠，包含九种状态、57 个有效输出格。

[下载安装包](https://github.com/Andonis75/codex-various-pet/releases/download/v0.1.0/headphone-boy.zip) · [安装说明](../README.md) · [透明雪碧图](spritesheet.png) · [角色配置](pet.json)

雪碧图为 RGBA PNG，1536×1872；安装包内只有 `headphone-boy/pet.json` 和 `headphone-boy/spritesheet.png`。预览按状态顺序展示，不代表 Codex 在桌面上的动作调度顺序。

## Rebuild this example

These transparent images were generated for this project through a browser-based image tool. They are included under the repository's MIT license as a reproducible example, rather than a requirement to use this character.

Run `various-pet demo ./demo-pet` to copy the eight original generated strips and their relative assembly settings into a new project. Then run `build`, `preview`, review it visually, `approve` and `install` with a new slug. The left-running row mirrors the approved right-running row. Deliberate held frames and the limited edge cleanup are recorded in the example's `source/assembly.json` and build reports.

`demo.gif` shows the effective animation cells in sequence using the v1 playback timings. `spritesheet.png` is the finished atlas. A successful geometric check does not guarantee stylistic consistency or smooth motion for every future generated character.
