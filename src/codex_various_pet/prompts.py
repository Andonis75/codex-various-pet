"""Provider-free prompts for an agent or a human using an existing browser."""
from __future__ import annotations

from pathlib import Path

from .project import child, config

ACTIONS = {
    "idle": "待机6帧：自然站立、吸气微抬、半闭眼、眨眼、睁眼呼气、回到初始姿势。脚底基线不动。",
    "running-right": "向右跑8帧：右脚触地、压低、双腿交错通过、腾空、左脚触地、压低、反向交错通过、腾空。必须有交替落脚和收腿，首尾连贯。",
    "running-left": "向左跑8帧：与右跑一样有交替落脚、收腿和腾空。只有角色左右对称时才可在本地逐帧镜像右跑，并保持时间顺序。",
    "waving": "挥手4帧：抬起手、向外摆、向内摆、放下回到原姿势。角色身体和双脚保持稳定。",
    "jumping": "跳跃5帧：准备、下蹲蓄力、腾空最高点、下降、落地缓冲。使用同一画布地面参考，最高点的脚底必须真的比站立时高，禁止每帧自动贴底。",
    "failed": "挫败8帧：意外、失落、低头、轻轻挠头、叹气闭眼、再睁眼、恢复、回到初始状态。表现温和，不加文字、符号或特效。",
    "waiting": "等待6帧：自然等候、略偏头、眨眼、看向旁边、轻微回头、恢复。脚底保持同一基线，不加气泡或动作线。",
    "running": "工作6帧：专注操作一个适合角色的小道具、左右操作、轻微点头、眨眼、继续操作、恢复。running在这里是工作状态，不是跑步。四足或特殊身体结构不要强行改成人类。",
    "review": "检查成果6帧：查看一个简单成果、观察、思考、轻微点头、满意、恢复。保持角色身体结构，不强行增加人类的手，禁止漂浮符号或文字。",
}


def generate(root: Path) -> Path:
    project = config(root)
    identity_path = child(root, "identity.md")
    identity = identity_path.read_text(encoding="utf-8-sig") if identity_path.exists() else "以我上传的参考图为角色外观依据。"
    common = (
        f"角色：{project['display_name']}。\n身份约束：{identity.strip()}\n"
        "继续使用本对话同一角色，保留可辨认的脸、发型/毛色、配饰、服装、身体结构和画风。采用一致Q版比例。\n"
        "实际生成单排完整全身动作图，真正透明背景PNG；人物等距，动作之间有宽阔完全透明留白，左右两端留大空隙。"
        "各姿势大小相同，不裁切头、耳朵、尾巴或脚，不让相邻角色接触；视角不漂移，除跳跃外脚底基线固定。"
        "不要场景、地面、阴影、棋盘格、文字编号、格线、动作线或特效。\n"
    )
    sections = ["# 网页端动作生成提示\n", "先把参考图上传至你已登录的网页对话，再按状态逐条发送。下载原始PNG，不截屏。每轮检查后再继续，失败时只重做该状态。\n"]
    for name, action in ACTIONS.items():
        sections.append(f"## {name} → source/{name}-strip.png\n\n{common}{action}\n")
    output = child(root, "prompts.md")
    output.write_text("\n".join(sections), encoding="utf-8")
    return output
