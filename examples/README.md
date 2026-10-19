# 成品桌宠 / Finished pets

| 角色 / Pet | 预览与成品 / Preview | 下载 / Download |
| --- | --- | --- |
| 耳机少年 / Headphone Boy | [动图、雪碧图与说明](headphone-boy/) | [headphone-boy.zip](https://github.com/Andonis75/codex-various-pet/releases/download/v0.1.0/headphone-boy.zip) |
| 樱桃喵 / Cherry Cat | [动图、雪碧图与说明](pink-cat-coder/) | [pink-cat-coder.zip](https://github.com/Andonis75/codex-various-pet/releases/download/v0.1.0/pink-cat-coder.zip) |

## 安装成品

1. 下载所选 ZIP，将其中的角色文件夹解压到 Codex 的 `pets` 目录。Windows 默认是 `%USERPROFILE%\.codex\pets\`，macOS/Linux 默认是 `~/.codex/pets/`。自定义了 `CODEX_HOME` 时，使用该目录下的 `pets/`。
2. 确认结构为 `pets/<角色文件夹>/pet.json` 和 `pets/<角色文件夹>/spritesheet.png`，不要额外嵌套一层目录。同名目录已存在时，保留旧目录，给新文件夹使用另一个名字。
3. 在 Codex 的宠物选择界面刷新列表并选择角色。文件安装与应用内选中是两个步骤。

ZIP 只包含角色目录内的 `pet.json` 和 `spritesheet.png`，无需运行脚本或重新生图。下载校验见 [pets-SHA256SUMS.txt](https://github.com/Andonis75/codex-various-pet/releases/download/v0.1.0/pets-SHA256SUMS.txt)。

## Install a finished pet

Download the ZIP and extract its character folder into your Codex `pets` directory: `%USERPROFILE%\.codex\pets\` on Windows or `~/.codex/pets/` on macOS/Linux. If you set `CODEX_HOME`, use its `pets/` subdirectory. Each character folder must directly contain `pet.json` and `spritesheet.png`. Keep existing pets; use a new folder name if one already exists. Refresh the pet selector in Codex and select the character.

Each download contains only the manifest and finished atlas. No image generation or script execution is needed. These are local Codex desktop v1 pets, not ChatGPT Work uploads.

想用自己的图制作新桌宠，返回[仓库首页](../README.md)，把仓库链接、参考图和需求交给 Codex。To make your own character, follow the request on the [repository homepage](../README.en.md).
