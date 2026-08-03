---
name: context-switcher
description: |
  任务切换与上下文压缩工具。当用户说"切换任务/清空上下文/换话题/回到XX"时触发。
  ⚠️ 强制执行：加载本Skill后，必须在本轮对话中调用 terminal 执行 scripts/context_switch.py。
  禁止用自然语言模拟执行结果。回复末尾必须粘贴脚本的原始stdout输出。
  如果未调用脚本或未粘贴输出，视为本Skill执行失败。
version: 1.2.0
metadata:
  hermes:
    tags: [context, task-switching, memory, productivity]
    related_skills: [knowledge-base]
  required_commands:
    - python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py
---

# 任务切换与上下文管理

## 🚨 强制执行要求（必读）

**加载本 Skill 不等于执行本 Skill。**

本 Skill 的核心执行体是 `scripts/context_switch.py`。`skill_view()` 只加载说明文档，**不会自动执行任何命令**。必须在同一轮内通过 `terminal` 调用以下脚本，否则视为未完成：

| 阶段 | 触发时机 | 必须执行的命令 |
|------|---------|--------------|
| 压缩当前上下文 | 用户要求切换/清理上下文时 | `python3 context_switch.py save "话题" --status "..." --bg "..." --exec "..." --decisions "..." --todos "..." --refs "..."` |
| 检索历史上下文 | 保存完成后 | `python3 context_switch.py confirm "关键词" --days 90` |
| 加载选中的上下文 | 用户回复选择编号后 | `python3 context_switch.py load "关键词" --selection "1,2" --days 90` |
| 环境检查 | 执行前（推荐） | `python3 context_switch.py check` |

**禁止仅凭 `skill_view()` 就回答"已处理"或"已完成切换"。** 必须看到脚本输出成功结果才算完成对应阶段。

## 概述

本 Skill 实现**任务切换时的上下文无损压缩与恢复**。当用户要求切换任务时，Agent 会自动完成两件事：

1. **压缩存储**：从当前对话中抽取核心关键要素，存储到当日临时记忆文件
2. **上下文恢复**：快速读取用户提到的新任务相关上下文，为新任务提供背景

**核心价值**：避免长会话中的上下文浪费，保持任务切换的连续性。

## 触发条件

当用户表达以下意图时，立即激活本 Skill：

### 明确触发词
- "清空上下文"
- "切换任务"
- "现在进行关于XX的任务"
- "换一个任务"
- "回到XX话题"
- "暂停当前，做XX"

### 隐式触发
- 用户开始讨论一个**完全不同领域**的话题（如从"部署服务器"跳到"写文章"）
- 用户明确说"忘了前面的，我们谈XX"

## 执行流程

### 阶段1：识别与确认

当检测到切换意图时，先确认：

```
识别到您要切换任务。是否压缩当前上下文并开始新任务？
当前话题：{简要概括}
新任务：{用户提到的内容}
```

**注意**：如果用户只是轻微转向（如从A功能扩展到B功能），不触发本 Skill。

### 阶段2：压缩当前上下文

从当前会话中提取以下核心要素：

#### 必存要素
1. **话题起源**：当前任务是如何开始的（用户初始需求）
2. **执行状态**：已完成/进行中/失败，关键步骤
3. **关键决策**：用户做出的选择、修改、偏好
4. **当前结果**：现在的位置、文件路径、状态

#### 存储格式

存储到文件：`~/.hermes/memory/daily/YYYY-MM-DD.md`

```markdown
## 会话快照 - HH:MM

**话题**：{一句话概括}
**状态**：{进行中/已完成/暂停}

### 背景
{话题起源，2-3句话}

### 执行情况
{已完成步骤，当前状态}

### 用户决策
- {关键选择1}
- {关键选择2}

### 待办/遗留
- {未完成事项}

### 关键引用
- 文件：{path}
- 链接：{url}
- 命令：{cmd}
```

### 阶段3：压缩当前上下文（必须执行，不可跳过）

**在本轮对话中立即执行以下命令**（禁止用自然语言复述）：

```bash
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py save \
"{当前话题标题}" \
--status "{进行中/已完成/暂停}" \
--bg "{话题起源，2-3句话}" \
--exec "{已完成步骤}" \
--decisions "{决策1|决策2}" \
--todos "{待办1|待办2}" \
--refs "{文件:path,链接:url}"
```

执行后，必须将终端输出的原始结果完整粘贴到回复中。

❌ 错误示例："已保存当前上下文到 memory 文件"
✅ 正确示例：粘贴脚本输出的 ✅ 已保存快照到 ~/.hermes/memory/daily/2026-08-03.md 等原始内容

### 阶段4：读取新任务上下文

检查用户提到的"XX"是否在以下位置有相关上下文：

1. **记忆关键词索引**（新增）：使用 `context_switch.py confirm <keyword>` 检索过去90天的相关记忆
2. **知识库**：使用 `kb_search.py` 搜索关键词
3. **历史会话**：使用 `session_search` 搜索相关对话
4. **当日记忆**：检查 `~/.hermes/memory/daily/` 中是否有相关记录

如果有，**通过索引检索并让用户确认**：

```
🔍 找到 X 条与"XX"相关的历史记忆：

[1] 2026-07-28 17:20 - 桨板6km训练计划
    预览：用户需要为老婆制定桨板6km训练计划...

[2] 2026-07-29 09:15 - 桨板饮食调整
    预览：根据7/28训练结果调整饮食方案...

💡 请回复数字编号（如"1"或"1,2"）选择要加载的记忆，
   或回复"全部"加载所有，或回复"取消"放弃。
```

用户选择后，加载完整上下文并展示：

```
📋 已加载 1 条历史记忆：

============================================================
📅 2026-07-28 17:20 | 桨板6km训练计划
============================================================
## 会话快照 - 17:20

**话题**：桨板6km训练计划HTML生成与部署
**状态**：部署中

### 背景
用户需要为老婆制定桨板6km训练计划，包含饮食建议...

[完整快照内容...]
```

**注意**：只有当检索到相关记忆时才展示确认界面，否则直接进入阶段5。

### 阶段5：执行切换

1. 确认存储成功
2. 开始新任务，引用已确认的上下文
3. 更新当前会话的"活跃话题"标记

## 记忆索引系统

### 索引结构

记忆索引位于：`~/.hermes/memory/index/keyword_index.json`

索引内容：从每个会话快照中提取关键词，建立倒排索引

```json
{
  "桨板训练": [
    {
      "date": "2026-07-28",
      "time": "17:20",
      "topic": "桨板6km训练计划HTML生成与部署",
      "file": "2026-07-28.md"
    }
  ],
  "饮食": [
    {
      "date": "2026-07-28",
      "time": "17:20",
      "topic": "桨板6km训练计划HTML生成与部署",
      "file": "2026-07-28.md"
    },
    {
      "date": "2026-07-29",
      "time": "09:15",
      "topic": "桨板饮食调整",
      "file": "2026-07-29.md"
    }
  ]
}
```

### 索引维护

#### 自动增量更新

每次保存上下文快照时，自动提取关键词并更新索引：

```bash
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py save \
  "话题标题" \
  --status "状态" \
  --bg "背景" \
  --exec "执行情况" \
  --decisions "决策1|决策2" \
  --todos "待办1|待办2" \
  --refs "文件:path,链接:url"
```

#### 手动重建索引

如需重建完整索引（扫描过去90天）：

```bash
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py rebuild [days]
```

#### 查看索引统计

```bash
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py stats
```

输出示例：
```json
{
  "status": "正常",
  "total_keywords": 156,
  "total_entries": 89,
  "covered_files": 15,
  "date_range": {
    "earliest": "2026-07-15",
    "latest": "2026-07-30"
  }
}
```

### 检索流程

#### 1. 确认检索（推荐）

```bash
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py confirm "桨板" --days 90
```

输出：
```
🔍 找到 2 条与"桨板"相关的历史记忆：

[1] 2026-07-28 17:20 - 桨板6km训练计划HTML生成与部署
    预览：用户需要为老婆制定桨板6km训练计划...

[2] 2026-07-29 09:15 - 桨板饮食调整
    预览：根据7/28训练结果调整饮食方案...

💡 请回复数字编号（如"1"或"1,2"）选择要加载的记忆...
```

#### 2. 加载完整上下文

用户选择后（如回复"1"）：

```bash
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py load "桨板" --selection "1" --days 90
```

输出：
```
📋 已加载 1 条历史记忆：

============================================================
📅 2026-07-28 17:20 | 桨板6km训练计划
============================================================
## 会话快照 - 17:20
...
```

### 关键词提取策略

索引系统自动从以下字段提取关键词：

1. **话题标题**：主要关键词
2. **背景说明**：场景关键词
3. **执行情况**：技术关键词
4. **用户决策**：选择关键词
5. **待办事项**：任务关键词
6. **关键引用**：文件/链接关键词

提取规则：
- **中文**：提取2-4字词组，过滤停用词
- **英文**：提取3字母以上单词，转小写，过滤停用词
- **数字**：保留数字串（如日期、版本号）
- **去重**：同一快照的关键词自动去重

### 清理策略

- **daily/** 中的文件超过 7 天自动清理（可通过 cronjob 实现）
- **index/** 中的索引文件与 daily/ 同步清理
- 清理前自动重建索引，确保剩余记忆可检索

### 快速命令

```bash
# 保存上下文快照（自动更新索引）
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py save \
  "话题标题" \
  --status "状态" \
  --bg "背景" \
  --exec "执行情况" \
  --decisions "决策1|决策2" \
  --todos "待办1|待办2" \
  --refs "文件:path,链接:url"

# 检索并确认加载（跨会话）
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py confirm "关键词" --days 90

# 根据选择加载完整上下文
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py load "关键词" --selection "1,3" --days 90

# 搜索（仅预览，不确认加载）
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py search "关键词" --days 7

# 重建索引（扫描过去90天）
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py rebuild 90

# 查看索引统计
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py stats

# 读取今日所有快照
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py read

# 清理7天前的临时记忆
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py cleanup 7
```

## 与记忆系统的集成

本 Skill 与 `memory` 工具配合使用：

- **短期压缩**：使用 `write_file` 写入 `daily/` 目录
- **长期提取**：重要事实使用 `memory` 工具存入持久化记忆
- **历史检索**：使用 `session_search` 查找历史会话
- **跨会话召回**：使用关键词索引检索过去90天的记忆，通过确认机制精准调取

## 错误处理

1. **存储失败**：如果无法写入文件，降级为仅内存压缩，提示用户
2. **索引损坏**：自动重建索引
3. **磁盘空间不足**：清理最旧的 daily 文件和索引
4. **权限问题**：检查 `~/.hermes/memory/` 目录权限

## 注意事项

- **触发准确性**：避免在正常对话中误触发，需确认是真正的任务切换
- **压缩质量**：不要过度压缩导致丢失关键细节，也不要保留无关信息
- **隐私保护**：daily 文件包含会话内容，注意权限设置
- **索引范围**：默认90天，可根据需要调整
- **确认机制**：检索结果必须经用户确认后再加载，避免误调用无关上下文

### 示例1：明确切换

**用户**：清空上下文，现在进行关于"珍珠行业分析"的任务

**Agent执行**：
1. 识别切换意图
2. 压缩当前上下文（假设之前在做"桨板训练计划"）：
   ```markdown
   ## 会话快照 - 17:20
   
   **话题**：桨板6km训练计划HTML生成与部署
   **状态**：部署中
   
   ### 背景
   用户需要为老婆制定桨板6km训练计划，包含饮食建议，生成HTML可视化页面。
   
   ### 执行情况
   - HTML已生成：/home/ubuntu/.hermes/output/桨板6km训练计划_饮食版.html
   - 已添加7/28训练数据看板
   - 部署到服务器8899端口，但公网超时（需开安全组）
   
   ### 用户决策
   - 选择部署到服务器而非飞书
   - 开新端口8899
   
   ### 待办
   - 开放云服务商安全组8899端口
   ```
3. 存储到 `~/.hermes/memory/daily/2026-07-28.md`
4. 搜索"珍珠行业分析"相关上下文：
   - 知识库中已有"珍珠行业全景分析.html"
   - 历史会话中讨论过配图问题
5. 展示给用户，开始新任务

### 示例2：隐式切换

**用户**：（之前在做Python调试）对了，帮我写一个微信公众号文章标题

**Agent执行**：
1. 检测到话题从"技术调试"跳到"内容创作"
2. 确认是否切换
3. 用户确认后，压缩存储调试上下文
4. 开始新任务

## 与记忆系统的集成

本 Skill 与 `memory` 工具配合使用：

- **短期压缩**：使用 `write_file` 写入 `daily/` 目录
- **长期提取**：重要事实使用 `memory` 工具存入持久化记忆
- **历史检索**：使用 `session_search` 查找历史会话

## 错误处理

1. **存储失败**：如果无法写入文件，降级为仅内存压缩，提示用户
2. **磁盘空间不足**：清理最旧的 daily 文件
3. **权限问题**：检查 `~/.hermes/memory/` 目录权限

## 注意事项

- **触发准确性**：避免在正常对话中误触发，需确认是真正的任务切换
- **压缩质量**：不要过度压缩导致丢失关键细节，也不要保留无关信息
- **隐私保护**：daily 文件包含会话内容，注意权限设置
- **清理机制**：定期清理 old daily 文件，避免磁盘占用

## 执行自检清单（Agent 回复前必填）

在提交回复前，逐项确认：
- [ ] 我是否在 terminal 中调用了 `context_switch.py` 脚本？
- [ ] 我是否粘贴了脚本的原始 stdout/stderr 输出？
- [ ] 如果用户要求加载历史记忆，我是否先执行了 `confirm` 并等待用户选择？
- [ ] 如果以上任一项为否，我的回复无效，必须重新执行。

**记住：写文档不等于执行。只有脚本输出才算数。**

## 快速命令

## 🚨 执行警告

以下所有命令都**必须通过 terminal 实际运行**，禁止用自然语言描述"我已执行"。
每次运行后，**必须粘贴原始输出**作为执行证据。

```bash
# 手动查看当日记忆
cat ~/.hermes/memory/daily/$(date +%Y-%m-%d).md

# 清理7天前的临时记忆
find ~/.hermes/memory/daily/ -name "*.md" -mtime +7 -delete
```

## 配套脚本

使用 `scripts/context_switch.py` 执行实际存储操作：

```bash
# 保存上下文快照
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py save \
  "桨板训练计划部署" \
  --status "部署中" \
  --bg "用户需要为老婆制定桨板6km训练计划..." \
  --exec "HTML已生成；已部署到8899端口；公网需开安全组" \
  --decisions "选择部署到服务器|开新端口8899" \
  --todos "开放云服务商安全组8899端口" \
  --refs "文件:/home/ubuntu/.hermes/output/桨板6km训练计划_饮食版.html,端口:8899"

# 读取今日所有快照
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py read

# 搜索关键词
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py search "珍珠"

# 清理7天前的临时记忆
python3 ~/.hermes/skills/productivity/context-switcher/scripts/context_switch.py cleanup
```

## 版本历史

- **v1.2.0** (2026-07-31)
  - 新增 🚨 强制执行要求章节（在 SKILL.md 最顶部）
  - 明确禁止仅凭 `skill_view()` 就认为 skill 已执行
  - 增加 `required_commands` metadata，声明核心执行脚本
  - 新增 `check` 命令（pre-flight 环境检查）

- **v1.1.0** (2026-07-30)
  - 新增关键词索引检索维度（跨会话记忆召回）
  - 支持自动增量更新索引（save 时自动提取关键词）
  - 支持手动重建索引（rebuild，默认90天）
  - 新增 confirm/load 交互命令（检索确认 -> 精准调取）
  - 新增 stats 命令查看索引统计
  - 搜索范围扩展：默认7天，confirm/load 默认90天
  - 关键词提取策略：中文2-4字词组 + 英文3字母单词 + 停用词过滤

- **v1.0.0** (2025-07-28)
  - 初始版本
  - 支持上下文压缩与存储
  - 支持新任务上下文检索
  - 集成知识库与会话搜索
  - 配套 Python 脚本