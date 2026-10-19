# 文档导航

面向 Codex **桌面本地宠物 v1**。图像生成走用户选择的网页流程；ChatGPT Work 云端 Pets 不在当前安装范围内。

- [中文使用说明](../README.md)：仓库链接与附图一句话，让代理准备环境并完成网页制作、本地安装。
- [English quick start](../README.en.md)：英文快速流程。
- [浏览器执行流程](../src/codex_various_pet/data/skill/references/browser-playbook.md)：上传、原图下载、逐状态重试、实际播放和安装。
- [网页生成与九状态提示](../src/codex_various_pet/data/skill/references/web-generation.md)：角色身份块、真实原图下载、逐行动作、失败重试。
- [v1 格式与人工验收](../src/codex_various_pet/data/skill/references/format.md)：行列、有效帧、原生节奏、manifest、检查界限。
- [排错与恢复](../src/codex_various_pet/data/skill/references/troubleshooting.md)：背景、裁切、姿势计数、安装和网页问题。
- [Codex 技能入口](../src/codex_various_pet/data/skill/SKILL.md)：代理按当前可用工具执行的流程。
- [高级 CLI 与手动回退](advanced-cli.md)：调试、示例、已有源图处理与无浏览器时的手动方式。

长版文档随技能放在 `references/`，由 Python 包一起分发。`install-skill` 复制同一份正文与运行入口，避免源码文档和安装技能各维护一套不同格式。

当前格式已在 Codex 桌面 `26.1013` 核验；其他版本需要实际验证。官方功能入口：[Pets](https://learn.chatgpt.com/docs/pets)。兼容性验证应分别记录“图像已下载”“构建已通过”“人工已看完”“文件已安装”“应用已显示”，其中任一阶段成功都不替代后面的验证。
