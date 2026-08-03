#!/usr/bin/env python3
"""
任务切换上下文压缩与存储脚本
当用户说"清空上下文，现在进行关于XX的任务"时使用
"""
import os
import re
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Hermes memory 目录
MEMORY_DIR = Path.home() / ".hermes" / "memory"
DAILY_DIR = MEMORY_DIR / "daily"
INDEX_DIR = MEMORY_DIR / "index"
INDEX_FILE = INDEX_DIR / "keyword_index.json"

# 停用词（中文 + 英文）
STOPWORDS = {
    # 中文
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "我们", "没有", "好", "自己", "这", "他", "她", "它", "们", "那", "些", "什", "么", "怎", "吗", "呢", "啊", "呀", "嗯",
    "吧", "还", "把", "让", "给", "从", "向", "对", "与", "及", "等", "但", "而", "或", "且", "并", "如果", "因为", "所以",
    # 英文
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall", "to", "of", "in", "for", "on", "with", "at",
    "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "because", "but", "and", "or", "if", "while", "although", "though", "until",
    "while", "since", "whether", "while", "unless", "provide", "provided", "that", "this", "these", "those", "it"
}


def ensure_dirs():
    """确保目录存在"""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)


def extract_keywords(text: str) -> list:
    """
    从文本中提取关键词
    
    策略：
    1. 中文：按字/词提取，过滤停用词，保留2字以上词语
    2. 英文：按单词提取，过滤停用词
    3. 合并去重
    """
    keywords = set()
    
    # 中文：提取2-4字词组
    # 先找所有连续的汉字串
    chinese_phrases = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
    for phrase in chinese_phrases:
        # 如果是长句，按2-4字滑动窗口提取
        if len(phrase) <= 4:
            if phrase not in STOPWORDS:
                keywords.add(phrase)
        else:
            # 长句按2-4字提取
            for i in range(len(phrase) - 1):
                for length in [2, 3, 4]:
                    if i + length <= len(phrase):
                        word = phrase[i:i+length]
                        if word not in STOPWORDS and len(word) >= 2:
                            keywords.add(word)
    
    # 英文：提取单词
    english_words = re.findall(r'[a-zA-Z]{3,}', text)
    for word in english_words:
        word_lower = word.lower()
        if word_lower not in STOPWORDS:
            keywords.add(word_lower)
    
    # 数字（如 7/30, 5km, 3 等）
    numbers = re.findall(r'\d+[\d/]*', text)
    keywords.update(numbers)
    
    return list(keywords)


def save_context_snapshot(topic: str, status: str, background: str, 
                          execution: str, decisions: list, 
                          todos: list, references: dict) -> str:
    """
    保存上下文快照到当日记忆文件，并更新关键词索引
    
    Returns:
        保存的文件路径
    """
    ensure_dirs()
    
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")
    filepath = DAILY_DIR / f"{today}.md"
    
    # 构建快照内容
    snapshot = f"""## 会话快照 - {now}

**话题**：{topic}
**状态**：{status}

### 背景
{background}

### 执行情况
{execution}

### 用户决策
"""
    for d in decisions:
        snapshot += f"- {d}\n"
    
    snapshot += "\n### 待办/遗留\n"
    for t in todos:
        snapshot += f"- {t}\n"
    
    snapshot += "\n### 关键引用\n"
    for key, value in references.items():
        snapshot += f"- {key}：{value}\n"
    
    snapshot += "\n---\n"
    
    # 追加到文件
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(snapshot)
    
    # 更新关键词索引
    update_index(today, now, topic, background, execution, decisions, todos, references)
    
    return str(filepath)


def update_index(date: str, time: str, topic: str, background: str, 
                 execution: str, decisions: list, todos: list, references: dict):
    """
    更新关键词索引（增量更新）
    
    索引结构：
    {
      "keyword": [
        {
          "date": "2026-07-28",
          "time": "17:20",
          "topic": "...",
          "file": "2026-07-28.md"
        },
        ...
      ]
    }
    """
    # 合并所有文本用于提取关键词
    all_text = f"{topic} {background} {execution} {' '.join(decisions)} {' '.join(todos)} {' '.join(references.values())}"
    keywords = extract_keywords(all_text)
    
    # 读取现有索引
    index = {}
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)
        except (json.JSONDecodeError, IOError):
            index = {}
    
    # 更新索引
    entry = {
        "date": date,
        "time": time,
        "topic": topic,
        "file": f"{date}.md"
    }
    
    for keyword in keywords:
        if keyword not in index:
            index[keyword] = []
        # 避免重复添加（相同日期+时间）
        if not any(e["date"] == date and e["time"] == time for e in index[keyword]):
            index[keyword].append(entry)
    
    # 保存索引
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def read_today_context() -> str:
    """读取今日所有上下文快照"""
    ensure_dirs()
    
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = DAILY_DIR / f"{today}.md"
    
    if not filepath.exists():
        return "今日暂无上下文记录。"
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def search_context(keyword: str, days: int = 7) -> list:
    """
    在历史记忆中搜索关键词（使用索引，默认范围7天）
    
    Args:
        keyword: 搜索关键词
        days: 搜索范围（天数），默认7天，None表示全部
    
    Returns:
        匹配的上下文列表，每个包含：date, time, topic, file, preview
    """
    ensure_dirs()
    results = []
    
    # 读取索引
    if not INDEX_FILE.exists():
        return results
    
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index = json.load(f)
    except (json.JSONDecodeError, IOError):
        return results
    
    keyword_lower = keyword.lower()
    
    # 计算日期范围
    cutoff_date = None
    if days is not None:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # 精确匹配 + 包含匹配
    matched_entries = []
    
    # 精确匹配
    if keyword_lower in index:
        matched_entries.extend(index[keyword_lower])
    
    # 包含匹配（关键词作为子串）
    for key, entries in index.items():
        if keyword_lower in key.lower() or key.lower() in keyword_lower:
            for entry in entries:
                if entry not in matched_entries:
                    matched_entries.append(entry)
    
    # 过滤日期范围
    if cutoff_date:
        matched_entries = [e for e in matched_entries if e["date"] >= cutoff_date]
    
    # 按日期+时间排序（最新的在前）
    matched_entries.sort(key=lambda e: (e["date"], e["time"]), reverse=True)
    
    # 读取完整上下文（preview）
    for entry in matched_entries:
        filepath = DAILY_DIR / entry["file"]
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 提取对应快照的完整内容
            snapshot_marker = f"## 会话快照 - {entry['time']}"
            if snapshot_marker in content:
                start_idx = content.index(snapshot_marker)
                # 找到下一个快照或文件结尾
                next_marker = content.find("\n## 会话快照 -", start_idx + 1)
                if next_marker != -1:
                    snapshot_content = content[start_idx:next_marker]
                else:
                    snapshot_content = content[start_idx:]
                
                results.append({
                    "date": entry["date"],
                    "time": entry["time"],
                    "topic": entry["topic"],
                    "file": entry["file"],
                    "preview": snapshot_content.strip()
                })
    
    return results


def confirm_and_load(keyword: str, days: int = 90) -> str:
    """
    关键词检索 + 确认后加载完整上下文（交互式）
    
    流程：
    1. 用索引检索过去90天的相关记忆
    2. 列出匹配结果，让用户确认
    3. 根据用户选择，加载完整上下文
    
    Returns:
        完整上下文内容，或提示信息
    """
    ensure_dirs()
    
    # 检索索引
    results = search_context(keyword, days=days)
    
    if not results:
        return f"未找到与\"{keyword}\"相关的历史记忆。"
    
    # 格式化输出供用户确认
    output = f"🔍 找到 {len(results)} 条与\"{keyword}\"相关的历史记忆：\n\n"
    
    for i, r in enumerate(results, 1):
        output += f"[{i}] {r['date']} {r['time']} - {r['topic']}\n"
        # 显示前100字预览
        preview = r['preview'][:100].replace('\n', ' ')
        output += f"    预览：{preview}...\n\n"
    
    output += "\n💡 请回复数字编号（如\"1\"或\"1,3\"）选择要加载的记忆，\n"
    output += "   或回复\"全部\"加载所有，或回复\"取消\"放弃。"
    
    return output


def load_selected_context(selection: str, keyword: str, days: int = 90) -> str:
    """
    根据用户选择加载完整上下文
    
    Args:
        selection: 用户选择（数字编号，如"1"或"1,3"或"全部"）
        keyword: 原始搜索关键词（用于重新检索）
        days: 搜索范围
    
    Returns:
        完整上下文内容
    """
    results = search_context(keyword, days=days)
    
    if not results:
        return f"未找到与\"{keyword}\"相关的历史记忆。"
    
    # 解析选择
    selected_indices = []
    if selection.strip().lower() in ["全部", "all"]:
        selected_indices = list(range(len(results)))
    else:
        try:
            # 支持 "1,3,5" 或 "1 3 5" 格式
            parts = selection.replace(",", " ").split()
            selected_indices = [int(p.strip()) - 1 for p in parts if p.strip().isdigit()]
            selected_indices = [i for i in selected_indices if 0 <= i < len(results)]
        except ValueError:
            return "选择格式错误，请输入数字编号（如\"1\"或\"1,3\"）。"
    
    if not selected_indices:
        return "未选择有效的历史记忆。"
    
    # 加载选中的完整上下文
    output = f"📋 已加载 {len(selected_indices)} 条历史记忆：\n\n"
    
    for idx in selected_indices:
        r = results[idx]
        output += f"{'='*60}\n"
        output += f"📅 {r['date']} {r['time']} | {r['topic']}\n"
        output += f"{'='*60}\n"
        output += r['preview']
        output += "\n\n"
    
    return output


def rebuild_index(days: int = 90):
    """
    重建关键词索引（扫描过去N天的所有记忆文件）
    
    Args:
        days: 重建范围（天数），默认90天
    """
    ensure_dirs()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    index = {}
    
    # 扫描所有daily文件
    for filepath in sorted(DAILY_DIR.glob("*.md")):
        filename = filepath.name
        date_str = filename.replace(".md", "")
        
        if date_str < cutoff_date:
            continue
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except IOError:
            continue
        
        # 解析所有快照
        sections = content.split("\n## 会话快照 - ")
        for section in sections[1:]:  # 跳过第一个空段
            lines = section.split("\n", 1)
            if not lines:
                continue
            
            time_str = lines[0].strip()
            
            # 提取快照各字段
            topic_match = re.search(r'\*\*话题\*\*：(.+)', section)
            bg_match = re.search(r'### 背景\n(.+?)(?=\n###|\Z)', section, re.DOTALL)
            exec_match = re.search(r'### 执行情况\n(.+?)(?=\n###|\Z)', section, re.DOTALL)
            decisions_match = re.findall(r'^- (.+)$', section, re.MULTILINE)
            
            # 提取待办和引用（简化处理）
            todos = []
            refs = {}
            decisions = [d.strip() for d in decisions_match] if decisions_match else []
            
            topic = topic_match.group(1).strip() if topic_match else ""
            background = bg_match.group(1).strip() if bg_match else ""
            execution = exec_match.group(1).strip() if exec_match else ""
            
            # 提取关键词
            all_text = f"{topic} {background} {execution} {' '.join(decisions)} {' '.join(todos)} {' '.join(refs.values())}"
            keywords = extract_keywords(all_text)
            
            # 添加到索引
            entry = {
                "date": date_str,
                "time": time_str,
                "topic": topic,
                "file": filename
            }
            
            for keyword in keywords:
                if keyword not in index:
                    index[keyword] = []
                if not any(e["date"] == date_str and e["time"] == time_str for e in index[keyword]):
                    index[keyword].append(entry)
    
    # 保存索引
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    return f"✅ 索引已重建，共索引 {len(index)} 个关键词，覆盖 {days} 天记忆。"


def list_index_stats() -> dict:
    """
    查看索引统计信息

    Returns:
        统计信息：关键词数量、覆盖文件数、日期范围
    """
    ensure_dirs()

    if not INDEX_FILE.exists():
        return {"status": "索引不存在，请先执行 rebuild"}

    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"status": "索引文件损坏"}

    # 统计
    all_dates = set()
    for entries in index.values():
        for entry in entries:
            all_dates.add(entry["date"])

    return {
        "status": "正常",
        "total_keywords": len(index),
        "total_entries": sum(len(entries) for entries in index.values()),
        "covered_files": len(all_dates),
        "date_range": {
            "earliest": min(all_dates) if all_dates else None,
            "latest": max(all_dates) if all_dates else None
        }
    }


def mark_session_suspended() -> str:
    """
    将当前会话标记为 suspended（方案B：归档后开新会话）。

    原理：Hermes gateway 在加载 sessions.json 时若发现条目 suspended=true，
    下次该会话收到消息时会 auto-reset（创建全新 session_id，旧消息不重放）。

    定位方式：优先使用 Hermes 注入的环境变量（HERMES_SESSION_*），
    匹配 sessions.json 中 origin.chat_id / platform / user_id。

    Returns:
        标记结果说明
    """
    sessions_file = Path.home() / ".hermes" / "sessions" / "sessions.json"
    if not sessions_file.exists():
        return "⚠️ 未找到 sessions.json，无法标记会话（归档已完成，请手动发送 /new 开新会话）"

    # 收集当前会话特征（agent 通过 terminal 运行时 Hermes 会注入这些环境变量）
    chat_id = os.environ.get("HERMES_SESSION_CHAT_ID", "").strip()
    platform = os.environ.get("HERMES_SESSION_PLATFORM", "").strip()
    user_id = os.environ.get("HERMES_SESSION_USER_ID", "").strip()
    thread_id = os.environ.get("HERMES_SESSION_THREAD_ID", "").strip()

    # 也接受命令行显式指定（--chat-id / --platform / --user-id）
    argv = sys.argv
    for flag, target in (("--chat-id", "chat_id"), ("--platform", "platform"), ("--user-id", "user_id")):
        if flag in argv:
            idx = argv.index(flag)
            if idx + 1 < len(argv):
                if target == "chat_id":
                    chat_id = argv[idx + 1].strip()
                elif target == "platform":
                    platform = argv[idx + 1].strip()
                elif target == "user_id":
                    user_id = argv[idx + 1].strip()

    if not chat_id and not platform and not user_id:
        return (
            "⚠️ 无法定位当前会话（环境变量和命令行参数都为空）。\n"
            "   请通过 terminal 运行本脚本（Hermes 会自动注入 HERMES_SESSION_* 环境变量），\n"
            "   或显式指定 --chat-id。归档已完成，请手动发送 /new 开新会话。"
        )

    try:
        with open(sessions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return f"⚠️ 读取 sessions.json 失败：{e}（归档已完成，请手动发送 /new）"

    matched = []
    for key, entry in data.items():
        origin = entry.get("origin", {}) or {}
        if chat_id and origin.get("chat_id") != chat_id:
            continue
        if platform and origin.get("platform") != platform:
            continue
        if user_id and origin.get("user_id") != user_id:
            continue
        matched.append((key, entry))

    if not matched:
        return (
            f"⚠️ 未找到匹配的会话条目（chat_id={chat_id or '?'}, platform={platform or '?'}）。\n"
            "   归档已完成，请手动发送 /new 开新会话。"
        )

    # 备份原文件（首次标记时）
    backup = sessions_file.with_name("sessions.json.bak-rotate")
    if not backup.exists():
        try:
            import shutil
            shutil.copy2(sessions_file, backup)
        except IOError:
            pass

    names = []
    for key, entry in matched:
        if not entry.get("suspended"):
            entry["suspended"] = True
        entry["auto_reset_reason"] = "context_switch_rotate"
        # 记录触发时间，便于排查
        entry["rotate_marked_at"] = datetime.now().isoformat(timespec="seconds")
        names.append(key.split(":")[-1] or key)

    try:
        with open(sessions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        return f"⚠️ 写入 sessions.json 失败：{e}（归档已完成，请手动发送 /new）"

    return (
        f"✅ 已标记 {len(matched)} 个会话为待重置（suspended=true）：{', '.join(names)}\n"
        f"   ▶ 立即生效：请发送 /new 开新会话（官方路径，旧消息不再重放）\n"
        f"   ▶ 自动生效：下次 gateway 重启后加载此标记，该会话自动开新窗口"
    )


def check_environment() -> str:
    """
    Pre-flight 环境检查：验证 context-switcher 依赖的目录、文件、脚本是否正常

    Returns:
        检查结果摘要
    """
    ensure_dirs()
    results = []

    # 1. 检查 daily/ 目录
    daily_ok = DAILY_DIR.exists() and DAILY_DIR.is_dir()
    results.append(("daily/ 目录", "✅ 正常" if daily_ok else "❌ 缺失", "高"))

    # 2. 检查 index/ 目录
    index_ok = INDEX_DIR.exists() and INDEX_DIR.is_dir()
    results.append(("index/ 目录", "✅ 正常" if index_ok else "❌ 缺失", "高"))

    # 3. 检查 keyword_index.json
    index_file_ok = INDEX_FILE.exists()
    results.append(("keyword_index.json", "✅ 存在" if index_file_ok else "⚠️ 不存在（首次使用请先执行 rebuild）", "高"))

    # 4. 检查索引状态
    if index_file_ok:
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)
            total_keywords = len(index)
            all_dates = set()
            for entries in index.values():
                for entry in entries:
                    all_dates.add(entry["date"])
            results.append((f"索引状态 ({total_keywords} 关键词, {len(all_dates)} 天)", "✅ 正常", "高"))
        except (json.JSONDecodeError, IOError):
            results.append(("索引状态", "❌ 索引文件损坏，请执行 rebuild", "高"))

    # 5. 检查今日 daily 文件
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = DAILY_DIR / f"{today}.md"
    today_ok = today_file.exists()
    results.append((f"今日记忆 {today}.md", "✅ 已创建" if today_ok else "⚠️ 今日暂无记录（save 后将自动创建）", "中"))

    # 汇总
    all_ok = all("✅" in r[1] for r in results)
    summary = "✅ 环境检查全部通过" if all_ok else "⚠️ 环境检查发现问题（见上方详情）"

    output = f"\n{summary}\n\n"
    output += "| 检查项 | 状态 | 优先级 |\n"
    output += "|--------|------|--------|\n"
    for name, status, priority in results:
        output += f"| {name} | {status} | {priority} |\n"

    return output


def main():
    if len(sys.argv) < 2:
        print("用法：")
        print("  python context_switch.py check")
        print("  python context_switch.py save <topic> --status <status> --bg <background> ...")
        print("  python context_switch.py rotate <topic> [--status <status>] [--bg ...] [--chat-id <id>]")
        print("      （方案B：归档 + 标记会话待重置，配合 /new 开新会话）")
        print("  python context_switch.py read")
        print("  python context_switch.py search <keyword> [--days <days>]")
        print("  python context_switch.py confirm <keyword> [--days <days>]")
        print("  python context_switch.py load <keyword> --selection <selection> [--days <days>]")
        print("  python context_switch.py rebuild [days]")
        print("  python context_switch.py stats")
        print("  python context_switch.py cleanup [days]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "rotate":
        """方案B：归档当前上下文 + 标记会话待重置（开新会话）"""
        # 先执行 save（归档快照 + 更新索引）
        topic = sys.argv[2] if len(sys.argv) > 2 else "未命名话题"
        status = "已归档"
        background = ""
        execution = ""
        decisions = []
        todos = []
        references = {}

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--bg" and i + 1 < len(sys.argv):
                background = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--exec" and i + 1 < len(sys.argv):
                execution = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--decisions" and i + 1 < len(sys.argv):
                decisions = sys.argv[i + 1].split("|")
                i += 2
            elif sys.argv[i] == "--todos" and i + 1 < len(sys.argv):
                todos = sys.argv[i + 1].split("|")
                i += 2
            elif sys.argv[i] == "--refs" and i + 1 < len(sys.argv):
                for pair in sys.argv[i + 1].split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        references[k.strip()] = v.strip()
                i += 2
            else:
                i += 1

        filepath = save_context_snapshot(
            topic=topic,
            status=status,
            background=background,
            execution=execution,
            decisions=decisions,
            todos=todos,
            references=references,
        )
        print(f"✅ 上下文已归档到：{filepath}")
        print()
        print(mark_session_suspended())

    elif command == "check":
        """Pre-flight 环境检查"""
        result = check_environment()
        print(result)

    elif command == "save":
        # 解析参数
        topic = sys.argv[2] if len(sys.argv) > 2 else "未命名话题"
        status = "进行中"
        background = ""
        execution = ""
        decisions = []
        todos = []
        references = {}
        
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--bg" and i + 1 < len(sys.argv):
                background = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--exec" and i + 1 < len(sys.argv):
                execution = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--decisions" and i + 1 < len(sys.argv):
                decisions = sys.argv[i + 1].split("|")
                i += 2
            elif sys.argv[i] == "--todos" and i + 1 < len(sys.argv):
                todos = sys.argv[i + 1].split("|")
                i += 2
            elif sys.argv[i] == "--refs" and i + 1 < len(sys.argv):
                # 格式：key1:value1,key2:value2
                for pair in sys.argv[i + 1].split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        references[k.strip()] = v.strip()
                i += 2
            else:
                i += 1
        
        filepath = save_context_snapshot(
            topic=topic,
            status=status,
            background=background,
            execution=execution,
            decisions=decisions,
            todos=todos,
            references=references
        )
        print(f"✅ 上下文已保存到：{filepath}")
    
    elif command == "read":
        content = read_today_context()
        print(content)
    
    elif command == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        if not keyword:
            print("请提供搜索关键词")
            sys.exit(1)
        
        days = 7
        if "--days" in sys.argv:
            days_idx = sys.argv.index("--days")
            if days_idx + 1 < len(sys.argv):
                days = int(sys.argv[days_idx + 1])
        
        results = search_context(keyword, days=days)
        if results:
            print(f"找到 {len(results)} 个匹配（最近{days}天）：\n")
            for i, r in enumerate(results, 1):
                print(f"=== 匹配 {i} ===\n")
                print(f"时间：{r['date']} {r['time']}")
                print(f"话题：{r['topic']}")
                print(f"文件：{r['file']}")
                print(f"\n内容预览：\n{r['preview'][:200]}...\n")
        else:
            print("未找到匹配内容。")
    
    elif command == "confirm":
        """交互式确认：检索后让用户选择要加载的记忆"""
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        if not keyword:
            print("请提供搜索关键词")
            sys.exit(1)
        
        days = 90
        if "--days" in sys.argv:
            days_idx = sys.argv.index("--days")
            if days_idx + 1 < len(sys.argv):
                days = int(sys.argv[days_idx + 1])
        
        result = confirm_and_load(keyword, days=days)
        print(result)
    
    elif command == "load":
        """根据用户选择加载完整上下文"""
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        if not keyword:
            print("请提供搜索关键词")
            sys.exit(1)
        
        selection = ""
        if "--selection" in sys.argv:
            selection_idx = sys.argv.index("--selection")
            if selection_idx + 1 < len(sys.argv):
                selection = sys.argv[selection_idx + 1]
        
        if not selection:
            print("请提供选择参数 --selection")
            sys.exit(1)
        
        days = 90
        if "--days" in sys.argv:
            days_idx = sys.argv.index("--days")
            if days_idx + 1 < len(sys.argv):
                days = int(sys.argv[days_idx + 1])
        
        result = load_selected_context(selection, keyword, days=days)
        print(result)
    
    elif command == "rebuild":
        """重建索引"""
        days = 90
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            days = int(sys.argv[2])
        
        result = rebuild_index(days=days)
        print(result)
    
    elif command == "stats":
        """查看索引统计"""
        stats = list_index_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    elif command == "cleanup":
        days = 7
        if len(sys.argv) > 2:
            days = int(sys.argv[2])
        cleanup_old_memory(days)
    
    else:
        print(f"未知命令：{command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
