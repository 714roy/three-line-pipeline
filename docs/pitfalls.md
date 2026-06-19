# 实战陷阱（Pitfalls）

> 三总六科管线在生产环境中踩过的 bug、设计缺陷和血泪教训。更新于 2026-06-19。

---

## 🔴 P1：Jinja2 模板不认识 Python 变量

**严重性：** 致命——管线崩溃

AgentFlow 在执行 shell 脚本前先用 Jinja2 渲染。`{{ variable }}` 只认 AgentFlow 上下文变量（如 `{{ nodes.节点名.output }}`），**不认** Python 模块级变量。

```python
# ❌ 崩溃：Jinja2 不知道 TASK 是什么
"{{ TASK }}"

# ✅ 正确：用 Python f-string + 文件注入
f"【任务】{TASK}"
```

**教训：** Python 变量和 Jinja2 模板变量是两个独立世界。任务文本通过临时文件传递，永远不要用 `{{ }}` 引用 Python 变量。

---

## 🔴 P2：并行节点的 `nodes.X.output[:N]` 切片崩溃

**严重性：** 致命——Jinja2 渲染 TypeError

当 shell 节点引用并行兄弟节点的输出：`{{ nodes.礼部.output[:3000] }}`——但兄弟节点还没执行，`output` 是 `None`，`None[:3000]` 抛出 TypeError。

```bash
# 修复：移除所有并行作用域内的 output 切片
sed -i 's/\.output\[:[0-9]*\]/.output/g' pipeline.py
```

**教训：** 永远不要假定并行节点的 output 就绪。只有对串行链中已完成的节点做切片才是安全的。

---

## 🟡 P3：Markdown 格式污染导致 KEY=VALUE 提取失败

**严重性：** 高——归档静默失败

LLM 在 markdown 上下文中会自然给输出值加 `**加粗**` 或 `| 表格 |` 格式。管线的 `grep "^OUTPUT_NAME="` 找到的是 `**OUTPUT_NAME=xxx**`，匹配不上。

```bash
# ❌ 遇到 **OUTPUT_NAME=xxx** 就跪
grep "^OUTPUT_NAME=" file.txt

# ✅ 通用格式都兼容
sed "s/^[* |]*//" file.txt | grep "^OUTPUT_NAME="
```

**影响的提取字段：** OUTPUT_NAME、ARCHIVE_PATH、MODE、TYPE、VERDICT、FEEDBACK、REWORK_TYPE——跨 3 个审核节点共 6+ 个字段。

**教训：** 所有 KEY=VALUE 提取必须先用 sed 剥离前导 markdown 格式。用 `sed "s/^[* |]*//"` 做通用前缀清理。

---

## 🟡 P4：MCP 工具输出噪音污染文档

**严重性：** 高——产出文件前 400 行是 JSON 垃圾

LLM 运行器加载 MCP 服务器（如 agentmemory）后，启动探针自动执行，原始 JSON 响应混入生成内容。

```bash
# 修复：督办处归档时加 MCP 噪音过滤
for f in "$DEST/产出/"*.md; do
  head -1 "$f" | grep -q "^\[tool agentmemory_" || continue
  sed -i "0,/^# /{//!d}" "$f"  # 删掉第一个标题前的所有内容
done
```

**教训：** 任何经过 MCP 运行器的 LLM 输出都可能被探针注入。归档步骤必须做过滤。

---

## 🟡 P5：入口脚本与管线目录不同步

**严重性：** 高——静默运行旧代码

入口脚本 `cd $TRSS_PIPELINE_DIR` 后跑 `agentflow run`。如果修复写到了源码树但没有重新部署到运行目录，管线静默运行旧代码。

```bash
# 加启动检查
if [ -f "$TRSS_PIPELINE_DIR/pipeline.py" ]; then
  SRC_MD5=$(md5sum "$SOURCE_TREE/pipeline.py" | cut -d' ' -f1)
  DEP_MD5=$(md5sum "$TRSS_PIPELINE_DIR/pipeline.py" | cut -d' ' -f1)
  if [ "$SRC_MD5" != "$DEP_MD5" ]; then
    cp "$SOURCE_TREE/pipeline.py" "$TRSS_PIPELINE_DIR/"
  fi
fi
```

**教训：** 修复源码树后必须重新部署到管线目录。加启动时 hash 校验。

---

## 🟡 P6：Python `-c` 内嵌带 `$` 的代码在 bash 上下文中崩溃

**严重性：** 高——shell 语法错误

在 `bash -c`（通过 AgentFlow 的 shell 执行器）中嵌入带 `$` 字符的 Python 代码（如正则结尾锚点），bash 将其解释为变量引用。

```python
# ❌ 崩溃：$ 被 bash 展开
python3 -c "re.compile(r'^(?:foo|bar$)', re.M)"

# ✅ 安全：写临时文件再执行
cat > /tmp/script.py << 'PYEOF'
import re
re.compile(r'^(?:foo|bar$)', re.M)
PYEOF
python3 /tmp/script.py
```

**教训：** 永远不要在内联 `python3 -c "..."` 中嵌入带 `$` 的 Python 代码。写临时文件。

---

## 🟡 P7：AgentFlow 并行调度导致 STOP 信号失效

**严重性：** 高——重复执行

AgentFlow 默认将**没有显式依赖关系的节点全部并行调度**。秘书处写的 STOP 文件（`/tmp/trss-STOP.txt`）其他节点看不到——因为它们已经启动了。

```bash
# 修复：在入口脚本层级预判，不依赖 AgentFlow 文件信号
ROUTE=$(reasonix precheck "$TASK")
if [ "$ROUTE" = "direct" ]; then
  reasonix answer "$TASK"
  exit 0  # 完全不调 agentflow
fi
agentflow run pipeline.py
```

**教训：** 文件信号在并行架构下不可靠。在脚本层级做预路由。

---

## 🟢 P8：不加引号的 Heredoc 展开 shell 变量

**严重性：** 中——提示词错误

```bash
cat > prompt.md << PROMPT_EOF   # 没引号——shell 展开 $VARS
cat > prompt.md << 'PROMPT_EOF' # 有引号——字面文本
```

写 LLM 提示词时用 **带引号的 heredoc**（`<< 'EOF'`）防止 `$` 被 shell 展开。

---

## 🟢 P9：重做循环第 2 轮丢失 MODE/TYPE

**严重性：** 中——所有节点在第 2 轮全部跳过

重做第 2 轮中，跳过的节点（如方案总第 2 轮跳过重拆）不输出 MODE/TYPE。如果临时文件被消耗或覆盖，下游节点拿到空 MODE → 全部 `[SKIP]` 退出。

```bash
# 修复：第 2 轮启动前从第 1 轮输出恢复 MODE/TYPE
if [ $ROUND -eq 2 ]; then
  grep -E '^MODE=' /tmp/_trss_ROUTE.txt > /tmp/trss-CUR-MODE.txt
  grep -E '^TYPE=' /tmp/_trss_REVIEW.txt > /tmp/trss-TYPE.txt
fi
```

**教训：** 重做循环必须从第 1 轮输出恢复状态，而不是从被跳过的第 2 轮输出获取。

---

## 🟢 P10：先判 Verdict 再归档导致产出丢失

**严重性：** 中——重做时产出被丢弃

原始设计先判 verdict 再归档。判重做时 `exit 0` 在 `cp` 之前执行，产出丢失——重做时没有东西可以改进。

**修复：** 先归档，再判 verdict。

---

## 总结

| # | 模式 | 类别 | 状态 |
|:--|:------|:------|:------|
| P1 | Jinja2 不认识 Python 变量 | AgentFlow | ✅ 已修复 |
| P2 | 并行节点 output 切片崩溃 | AgentFlow | ✅ 已修复 |
| P3 | Markdown 格式污染提取 | LLM 输出 | ✅ sed 前缀 |
| P4 | MCP 噪音注入 | LLM 运行器 | ✅ 督办处过滤 |
| P5 | 源码/运行目录不同步 | 部署 | ⚠️ 加检查 |
| P6 | Python `-c` 内嵌 `$` | Shell 脚本 | ✅ 临时文件 |
| P7 | 并行图文件信号失效 | AgentFlow | ✅ 预路由 |
| P8 | 未引号 heredoc | Shell 脚本 | ✅ 加引号 |
| P9 | 重做丢失 MODE/TYPE | 管线逻辑 | ✅ 已修复 |
| P10 | Verdict 先于归档 | 管线逻辑 | ✅ 先归档 |
