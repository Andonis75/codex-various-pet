# 高级 CLI 与手动回退

常用入口是把仓库链接和参考图交给 Codex，让它按 README/AGENTS 准备环境、读取技能并操作已登录网页完成后续。本文供调试、无浏览器工具时的手动回退，或只处理已有源图时使用。

## 源码环境与入口

```bash
git clone https://github.com/Andonis75/codex-various-pet.git
cd codex-various-pet
python tools/bootstrap.py
```

bootstrap 在仓库创建隔离 `.venv`，JSON 输出包含 `python`、`repo`、`version`。用其中的 Python 路径执行 `-m codex_various_pet` 和下述子命令。

也可以自行安装：

```bash
python -m pip install -e .
various-pet --help
```

命令不在 PATH 时，用 `python -m codex_various_pet` 加相同子命令。依赖应装在正在运行的同一个 Python 环境里。

## 不消耗生成额度的示例

```bash
various-pet demo ./demo-pet
various-pet inspect ./demo-pet
various-pet build ./demo-pet
various-pet preview ./demo-pet --open
```

`demo` 复制随包示例到新目录，不覆盖已有目录。`preview` 默认只写自包含 HTML，`--open` 才尝试打开浏览器。示例成功只验证这套源图的处理，不代替你自己的角色检查。

## 手动生成或已有动作条

```bash
various-pet init ./my-pet --reference ./cat.png --name "猫猫"
various-pet prompts ./my-pet
```

`--reference` 可选。编辑 `identity.md` 后重新运行 `prompts` 更新 `prompts.md`。网页可由你手动操作，也可由代理真实控制；Python CLI 本身不伪造浏览器生成。

将真实原图下载到 `source/`：

| 文件 | 状态 | 有效帧 |
|---|---|---:|
| `idle-strip.png` | 待机 | 6 |
| `running-right-strip.png` | 向右跑 | 8 |
| `running-left-strip.png` | 向左跑 | 8 |
| `waving-strip.png` | 挥手 | 4 |
| `jumping-strip.png` | 跳跃 | 5 |
| `failed-strip.png` | 挫败 | 8 |
| `waiting-strip.png` | 等候 | 6 |
| `running-strip.png` | 工作 | 6 |
| `review-strip.png` | 检查成果 | 6 |

提示见 [网页生成指南](../src/codex_various_pet/data/skill/references/web-generation.md)。保留已完成行，先检查再续做。假棋盘、缺帧、粘连和裁切应修源图，不靠改扩展名或删掉所有白色掩盖。

## 检查、构建、认可与安装

```bash
various-pet inspect ./my-pet
various-pet build ./my-pet
various-pet preview ./my-pet --open
```

阅读报告并实际播放预览，检查九状态身份、尺度、脚底、步态、跳跃与边缘。明确帧选择、镜像和尺度配置见 [格式与验收](../src/codex_various_pet/data/skill/references/format.md)。

运行者实际看完并认可当前构建后：

```bash
various-pet approve ./my-pet
various-pet install ./my-pet --slug my-pet
```

`approve` 非交互记录“我已看过当前构建”，不会替你判断图像；代理实际视觉审查且用户授权安装时，也可以由代理执行。哈希、几何和认可必须匹配；修改或重新构建后应重新观看并认可。

同名安装目录已存在会停止。装好后在 Codex 宠物选择界面选择新角色并确认显示。`CODEX_HOME` 和目的目录以实际输出为准。

## 导出 ZIP

```bash
various-pet package ./my-pet --slug my-pet
```

导出同样要求已审查的当前构建。只分享有权公开的图像，勿附私有聊天、账号信息或凭据。
