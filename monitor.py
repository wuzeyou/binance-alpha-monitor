#!/usr/bin/env python3
"""
Binance Alpha Airdrop Monitor
- 数据源: alpha123.uk
- 检测新空投 + 信息变更
- 输出 JSON 格式结果供 OpenClaw cron 读取推送
"""

import json
import os
import sys
import time
from datetime import datetime

# Cloudflare bypass
try:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
except ImportError:
    print("ERROR: cloudscraper not installed. Run: pip3 install cloudscraper", file=sys.stderr)
    sys.exit(1)

# ── 配置 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "state.json")
API_URL = "https://alpha123.uk/api/data?fresh=1"

# 监控字段
MONITOR_FIELDS = ["name", "time", "amount", "points", "type", "completed"]
FIELD_NAMES = {
    "name": "项目名称", "time": "时间", "amount": "数量",
    "points": "积分要求", "type": "类型", "completed": "状态"
}


def fetch_airdrops():
    """从 alpha123.uk 拉取空投数据"""
    try:
        resp = scraper.get(API_URL, timeout=30)
        print(f"DEBUG: HTTP {resp.status_code}, length={len(resp.text)}", file=sys.stderr)
        resp.raise_for_status()
        data = resp.json()
        airdrops = data.get("airdrops", [])
        print(f"DEBUG: got {len(airdrops)} airdrops", file=sys.stderr)
        return airdrops
    except Exception as e:
        print(f"ERROR: 获取数据失败: {e}", file=sys.stderr)
        return None


def load_state():
    """加载本地状态"""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    """保存状态"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def make_key(airdrop):
    """生成唯一 key: {token}_{date}_P{phase}"""
    token = airdrop.get("token", "UNKNOWN")
    date = airdrop.get("date", "")
    phase = airdrop.get("phase", 1)
    return f"{token}_{date}_P{phase}"


def normalize(value, field=""):
    """规范化字段值"""
    if value is None:
        return "否" if field == "completed" else ""
    if isinstance(value, bool):
        return "是" if value else "否"
    s = str(value).strip()
    if s.lower() in ["-", "none", "null", ""]:
        return ""
    if s.lower() == "false":
        return "否"
    if s.lower() == "true":
        return "是"
    return s


def detect_changes(old, new):
    """对比变化字段"""
    changes = []
    for f in MONITOR_FIELDS:
        ov = normalize(old.get(f), f)
        nv = normalize(new.get(f), f)
        if not ov and not nv:
            continue
        if ov != nv:
            changes.append({
                "field": FIELD_NAMES.get(f, f),
                "old": ov or "待公布",
                "new": nv or "待公布"
            })
    return changes


def snapshot(airdrop):
    """提取存储快照"""
    result = {}
    for k in ["token", "name", "date", "time", "amount", "points", "type", "phase", "completed"]:
        v = airdrop.get(k)
        # 对于 completed 字段，None/缺失时默认为 False
        if k == "completed" and v is None:
            v = False
        result[k] = v if v is not None else ""
    return result


def type_label(t):
    """空投类型中文"""
    return {"tge": "TGE", "grab": "先到先得", "warning": "预测"}.get(t, t or "")


def format_new(a):
    """格式化新空投消息"""
    token = a.get("token", "?")
    name = a.get("name", "?")
    date = a.get("date", "待公布")
    t = a.get("time", "")
    amount = a.get("amount", "-")
    points = a.get("points", "-")
    atype = type_label(a.get("type", ""))
    phase = a.get("phase", 1)

    time_str = f"{date} {t}" if t else date
    if phase == 2:
        time_str += " (二段)"

    lines = [
        f"🎁 新 Alpha 空投: {token}",
        f"项目: {name}",
        f"时间: {time_str}",
        f"数量: {amount}",
        f"积分: {points}",
    ]
    if atype:
        lines.append(f"类型: {atype}")
    lines.append(f"详情: https://alpha123.uk/zh/")
    return "\n".join(lines)


def format_update(a, changes):
    """格式化更新消息"""
    token = a.get("token", "?")
    lines = [f"📢 空投信息更新: {token}"]
    for c in changes:
        lines.append(f"  {c['field']}: {c['old']} → {c['new']}")
    lines.append(f"详情: https://alpha123.uk/zh/")
    return "\n".join(lines)


def check():
    """执行一次检查，返回需要推送的消息列表"""
    airdrops = fetch_airdrops()
    if airdrops is None:
        return None  # 请求失败

    state = load_state()
    messages = []

    for a in airdrops:
        key = make_key(a)

        if key not in state:
            # 新空投
            messages.append({"type": "new", "text": format_new(a), "token": a.get("token", "?")})
            state[key] = snapshot(a)
        else:
            # 检测变化
            changes = detect_changes(state[key], a)
            if changes:
                messages.append({"type": "update", "text": format_update(a, changes), "token": a.get("token", "?")})
                state[key] = snapshot(a)

    save_state(state)
    return messages


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        # 初始化模式：只存状态不推送（避免首次运行推一堆旧的）
        airdrops = fetch_airdrops()
        if airdrops is None:
            print("ERROR: init failed", file=sys.stderr)
            sys.exit(1)
        state = {}
        for a in airdrops:
            state[make_key(a)] = snapshot(a)
        save_state(state)
        print(f"OK: 初始化完成，记录了 {len(state)} 条空投")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "--dump":
        # 调试：显示当前所有空投
        airdrops = fetch_airdrops()
        if airdrops is None:
            sys.exit(1)
        for a in airdrops:
            print(json.dumps(a, ensure_ascii=False))
        sys.exit(0)

    # 正常检查模式
    messages = check()
    if messages is None:
        print("ERROR: check failed", file=sys.stderr)
        sys.exit(1)

    if not messages:
        print("OK: 没有新空投或更新")
    else:
        # 输出所有消息（每条一个 JSON 行）
        for m in messages:
            print(json.dumps(m, ensure_ascii=False))


if __name__ == "__main__":
    main()
