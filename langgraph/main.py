"""
三总六科 LangGraph 主图

用法：
  自动模式：python main.py "你的任务"
  交互模式：python main.py --interactive "你的任务"
  单步模式：python main.py --step "你的任务"
     （每跑一步等用户输入，y=继续 n=停 m=改方案）
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command
from langgraph.checkpoint.memory import MemorySaver

from lib.state import TaskState, default_state
from agents.san_sheng import (
    node_秘书处, node_方案总, node_门下省, 
    should_approve, MAX_REVIEW_ROUNDS
)
from agents.liu_bu import (
    node_执行总, node_六部, node_门下省复查,
    node_督办处, should_approve_output
)


def build_graph() -> StateGraph:
    """构建三总六科 LangGraph"""
    
    builder = StateGraph(TaskState)
    
    # ── 添加节点 ──
    builder.add_node("秘书处", node_秘书处)
    builder.add_node("方案总", node_方案总)
    builder.add_node("门下省", node_门下省)
    builder.add_node("执行总", node_执行总)
    builder.add_node("六部", node_六部)
    builder.add_node("门下省复查", node_门下省复查)
    builder.add_node("督办处", node_督办处)
    
    # ── 主流程 ──
    builder.add_edge(START, "秘书处")
    builder.add_edge("秘书处", "方案总")
    builder.add_edge("方案总", "门下省")
    
    # 门下省审核：通过→执行总，驳回→方案总
    builder.add_conditional_edges(
        "门下省",
        should_approve,
        {
            "approve": "执行总",
            "reject": "方案总",
        }
    )
    
    # 执行总 → 六部并行（第一阶段：生产部先跑，审计总后跑）
    def dispatch_production(state: TaskState):
        """Phase 1: 生产部先行（工程科/人事科/数据科/内容科/研发科/情报科），审计总等工程科出结果后再跑"""
        tasks = []
        for s in state.get("subtasks", []):
            if s.get("dept") != "审计总":
                tasks.append(Send("六部", {"subtask": s}))
        if not tasks:
            # 全是审计总 → 直接发
            for s in state.get("subtasks", []):
                tasks.append(Send("六部", {"subtask": s}))
        return tasks
    
    builder.add_conditional_edges("执行总", dispatch_production, {"六部": "六部"})
    
    # 六部 → 审计总分派（第二阶段） 或 → 门下省复查
    def dispatch_审计总_or_review(state: TaskState):
        """生产部跑完后，检查还有没有审计总待执行"""
        existing_results = state.get("results", {})
        pending_ids = set()
        for s in state.get("subtasks", []):
            if s.get("dept") == "审计总" and s.get("id") not in existing_results:
                pending_ids.add(s["id"])
        
        if not pending_ids:
            return "to_review"  # 没审计总了→去复查
        
        # 审计总启动：把工程科结果注入审计总prompt
        results_summary_lines = ["\n\n=== 工程科已完成产出（供审计总逐条核验）==="]
        for task_id, result in state.get("results", {}).items():
            results_summary_lines.append(f"\n--- {task_id} ---\n{str(result)[:3000]}")
        results_summary = "\n".join(results_summary_lines)
        
        tasks = []
        for s in state.get("subtasks", []):
            if s.get("id") in pending_ids:
                s["prompt"] = s.get("prompt", "") + results_summary
                s["status"] = "running"
                tasks.append(Send("六部", {"subtask": s}))
        return tasks
    
    builder.add_conditional_edges(
        "六部", dispatch_审计总_or_review,
        {
            "dispatch_审计总": "六部",  # 有审计总→再派一次
            "to_review": "门下省复查",
        }
    )
    
    # 复查路由
    def output_review_router(state: TaskState):
        if state.get("needs_imperial_decision", False):
            return "approve"  # 需裁决→先到督办处呈报
        if not state["output_review_passed"]:
            return "reject"
        return "approve"
    
    builder.add_conditional_edges(
        "门下省复查",
        output_review_router,
        {
            "approve": "督办处",
            "reject": "执行总",
        }
    )
    
    builder.add_edge("督办处", END)
    
    return builder


# ─── 运行模式 ───

NODES_TO_INTERRUPT = ["秘书处", "方案总", "门下省", "执行总", "六部", "门下省复查", "督办处"]


def get_state_summary(state: TaskState, node_name: str) -> str:
    """生成当前节点的状态摘要"""
    lines = []
    lines.append(f"📍 {node_name}")
    
    if node_name == "秘书处":
        lines.append(f"   意图：{state.get('intent', '')[:80]}")
        lines.append(f"   参数：{json.dumps(state.get('params', {}), ensure_ascii=False)[:120]}")
    
    elif node_name == "方案总":
        plan = state.get("plan", [])
        lines.append(f"   方案：{state.get('plan_rationale', '')[:150]}")
        for s in plan:
            lines.append(f"     - [{s.get('dept','?')}] {s.get('action','')[:60]}")
    
    elif node_name == "门下省":
        if not state.get("review_passed", True):
            lines.append(f"   驳回原因：{state.get('review_feedback', '')[:200]}")
        else:
            lines.append(f"   审核通过 ✅")
    
    elif node_name == "执行总":
        subs = state.get("subtasks", [])
        lines.append(f"   派发 {len(subs)} 个子任务：")
        for s in subs:
            lines.append(f"     - [{s.get('dept','?')}] {s.get('desc','')[:60]}")
    
    elif node_name == "六部":
        results = state.get("results", {})
        if results:
            for k, v in results.items():
                lines.append(f"     {k}: {v[:100]}...")
    
    elif node_name == "门下省复查":
        if not state.get("output_review_passed", True):
            lines.append(f"   复查驳回：{state.get('output_review_feedback', '')[:150]}")
        else:
            lines.append(f"   复查通过 ✅")
    
    elif node_name == "督办处":
        summary = state.get("summary", "")
        lines.append(f"   报告摘要：{summary[:200]}")
    
    return "\n".join(lines)


def run_sansheng(task: str, context: str = "", debug: bool = False, interactive: bool = False) -> TaskState:
    """
    运行三总六科图
    
    Args:
        interactive: True = 每步执行后检查 state，返回给前端（Hermes）
                     持续调用 resume_sansheng() 继续
    """
    builder = build_graph()
    
    # 交互模式：在关键节点前中断
    interrupt_nodes = ["秘书处", "方案总", "门下省", "六部", "门下省复查", "督办处"]
    
    graph = builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=interrupt_nodes if interactive else None,
    )
    
    initial = default_state(task, context)
    config = {"configurable": {"thread_id": "sansheng_liubu_001"}}
    
    if debug:
        print(f"📤 任务：{task}")
    
    # 首次运行（从 START 到第一个中断点）
    for event in graph.stream(initial, config, stream_mode="updates"):
        for node_name, state_update in event.items():
            if debug:
                status = "✅"
                if node_name == "门下省" and not state_update.get("review_passed", True):
                    status = "🔄"
                elif node_name == "门下省复查" and not state_update.get("output_review_passed", True):
                    status = "🔄"
                print(f"  {status} {node_name}")
    
    return graph, config


def resume_sansheng(graph, config, user_input: str = "continue", debug: bool = False) -> tuple:
    """
    从中断点继续运行三总六科图
    
    Args:
        user_input: "continue" 继续, "stop" 停止, "modify:xxx" 修改方案继续
    Returns:
        (graph, config, state, done) 
        done=True 表示全部跑完
    """
    if user_input.lower() == "stop":
        state = graph.get_state(config).values
        return graph, config, state, True
    
    # 正常继续
    try:
        for event in graph.stream(None, config, stream_mode="updates"):
            for node_name, state_update in event.items():
                if debug:
                    status = "✅"
                    if node_name == "门下省" and not state_update.get("review_passed", True):
                        status = "🔄"
                    elif node_name == "门下省复查" and not state_update.get("output_review_passed", True):
                        status = "🔄"
                    print(f"  {status} {node_name}")
    except Exception as e:
        # 可能是执行完了
        pass
    
    # 检查是否全部跑完
    state = graph.get_state(config)
    is_done = state.next == () or state.next is None or len(state.next) == 0
    
    return graph, config, state.values, is_done


# ─── CLI ───

if __name__ == "__main__":
    import sys
    
    args = sys.argv[1:]
    interactive = "--interactive" in args or "-i" in args
    args = [a for a in args if not a.startswith("--") and not a.startswith("-")]
    
    task = " ".join(args) if args else "分析《家庭、私有制与国家的起源》的核心论点"
    
    if interactive:
        graph, config = run_sansheng(task, debug=True, interactive=True)
        
        while True:
            state = graph.get_state(config).values
            next_nodes = graph.get_state(config).next
            
            if not next_nodes:
                print("\n" + "="*50)
                print("📜 督办处汇报")
                print("="*50)
                print(state.get("summary", "无输出"))
                print(f"\n💰 总成本: ${state.get('total_cost', 0):.4f}")
                break
            
            print(f"\n--- 下一步：{next_nodes} ---")
            
            # 显示当前状态摘要
            for nn in next_nodes:
                print(get_state_summary(state, nn))
            
            user_cmd = input("\n[y=继续 / n=停 / m=修改方案] > ").strip()
            
            resume_cmd = "continue"
            if user_cmd.lower() in ("n", "q", "stop", "exit"):
                resume_cmd = "stop"
            
            graph, config, state, done = resume_sansheng(graph, config, resume_cmd, debug=True)
            if done:
                print("\n" + "="*50)
                print("📜 督办处汇报")
                print("="*50)
                print(state.get("summary", "无输出"))
                print(f"\n💰 总成本: ${state.get('total_cost', 0):.4f}")
                break
    else:
        # 自动模式：一次跑完
        builder = build_graph()
        graph = builder.compile()
        initial = default_state(task, "")
        config = {"configurable": {"thread_id": "sansheng_liubu_001"}}
        
        print(f"📤 任务：{task}\n")
        
        # 取最后一条 event 的 state
        final_state = {}
        for event in graph.stream(initial, config, stream_mode="updates"):
            for node_name, state_update in event.items():
                status = "✅"
                if node_name == "门下省" and not state_update.get("review_passed", True):
                    status = "🔄"
                elif node_name == "门下省复查" and not state_update.get("output_review_passed", True):
                    status = "🔄"
                print(f"  {status} {node_name}")
                final_state.update(state_update)
        
        print("\n" + "="*50)
        print("📜 督办处汇报")
        print("="*50)
        print(final_state.get("summary", "无输出"))
        print(f"\n💰 总成本: ${final_state.get('total_cost', 0):.4f}")
