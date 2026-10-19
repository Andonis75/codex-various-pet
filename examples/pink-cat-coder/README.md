# 樱桃喵 / Cherry Cat

![樱桃喵九种动作预览](demo.gif)

粉色短发、猫耳、蓝绿色眼睛、代码发夹和奶白粉外套的 Q 版角色。这套成品来自独立新 Codex 对话测试：输入仓库链接和一张角色参考图，由代理操控已登录的 ChatGPT 网页，完成逐状态生成、下载、检查与重试、组装和本地安装。

[下载安装包](https://github.com/Andonis75/codex-various-pet/releases/download/v0.1.0/pink-cat-coder.zip) · [安装说明](../README.md) · [透明雪碧图](spritesheet.png) · [角色配置](pet.json)

## 成品信息

- 九种状态：待机、右跑、左跑、挥手、跳跃、挫败、等待、专注工作、检查成果，共 57 个有效格。
- RGBA PNG，1536×1872，单格 192×208；15 个未使用格全透明。
- 左右跑分别生成，保留非对称服饰。跳跃保留真实升降。
- 预览 GIF 按状态顺序展示，保留原生帧时长，不代表 Codex 桌面调度规则。
- 安装包只含 `pink-cat-coder/pet.json` 和 `pink-cat-coder/spritesheet.png`。

本次实测中人工处理过一次网页验证，完成后代理自行续做。不同动作间仍有轻微比例差异；这个例子展示已跑通的流程，不承诺所有账号和网页版本都可无人值守完成。

## About this example

A fresh Codex task received the repository URL and one reference image, operated the signed-in ChatGPT website, generated and checked nine animation states, then built and installed this pet. The asymmetric left and right runs were generated separately. One browser verification required human input. Minor cross-state proportion variation remains.

The download contains a local Codex desktop v1 manifest and a transparent 1536×1872 atlas with 57 effective cells. See the [installation guide](../README.md) to use it, or the [homepage](../../README.en.md) to create your own character.
