#!/usr/bin/env python3
"""
任务切换上下文压缩与存储脚本
当用户说"清空上下文，现在进行关于XX的任务"时使用
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Hermes memory 目录
MEMORY_DIR = Path.home() / ".hermes" / "memory"
DAILY_DIR = MEMORY_DIR / "daily"


def ensure_dirs():
    """确保目录存在"""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)


def save_context_snapshot(topic: str, status: str, background: str, 
                          execution: str, decisions: list, 
                          todos: list, references: dict) -> str:
    """
    保存上下文快照到当日记忆文件
    
    Args:
        topic: 话题标题（一句话）
        status: 状态（进行中/已完成/暂停）
        background: 背景说明（2-3句话）
        execution: 执行情况（已完成步骤，当前状态）
        decisions: 用户决策列表
        todos: 待办/遗留事项
        references: 关键引用（文件、链接、命令等）
    
    Returns:
        保存的文件路径
    """
    ensure_dirs()
    
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")
    filepath = DAILY_DIR / f"{today}.md"
    
    # 构建快照内容
    snapshot = f"""
## 会话快照 - {now}

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
    
    return str(filepath)


def read_today_context() -> str:
    """读取今日所有上下文快照"""
    ensure_dirs()
    
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = DAILY_DIR / f"{today}.md"
    
    if not filepath.exists():
        return "今日暂无上下文记录。"
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def search_context(keyword: str) -> list:
    """
    在当日记忆中搜索关键词
    
    Returns:
        匹配的快照列表
    """
    ensure_dirs()
    
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = DAILY_DIR / f"{today}.md"
    
    if not filepath.exists():
        return results
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 简单按段落分割搜索
    sections = content.split("\n## ")
    for section in sections:
        if keyword.lower() in section.lower():
            results.append(section.strip())
    
    return results


def cleanup_old_memory(days: int = 7):
    """清理超过指定天数的临时记忆"""
    import time
    
    cutoff = time.time() - (days * 86400)
    
    for filepath in DAILY_DIR.glob("*.md"):
        if filepath.stat().st_mtime < cutoff:
            filepath.unlink()
            print(f"🗑️ 已清理：{filepath.name}")


def main():
    if len(sys.argv) < 2:
        print("用法：")
        print("  python context_switch.py save <topic> --status <status> --bg <background> ...")
        print("  python context_switch.py read")
        print("  python context_switch.py search <keyword>")
        print("  python context_switch.py cleanup [days]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "save":
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
        
        results = search_context(keyword)
        if results:
            print(f"找到 {len(results)} 个匹配：\n")
            for i, r in enumerate(results, 1):
                print(f"=== 匹配 {i} ===\n{r}\n")
        else:
            print("未找到匹配内容。")
    
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        cleanup_old_memory(days)
    
    else:
        print(f"未知命令：{command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
