import streamlit as st
import threading
import queue
import sys
import io
import time
import re
import os
from datetime import datetime, timedelta

os.environ.setdefault("OPENROUTER_API_KEY", "ak_2ts7ug6nV9kn9C21tQ9pY17Z17H7n")

st.set_page_config(page_title="智能投研分析", page_icon="📊", layout="wide")

POPULAR_TICKERS = {
    "AAPL": "苹果", "NVDA": "英伟达", "TSLA": "特斯拉",
    "MSFT": "微软", "GOOGL": "谷歌", "META": "Meta",
    "AMZN": "亚马逊", "AMD": "AMD", "NFLX": "奈飞",
    "QQQ": "纳斯达克指数", "SPY": "标普500指数",
}

AGENT_LABELS = {
    "Market Analyst": ("📈", "技术分析师", "提取 MACD、RSI 等技术指标，识别交易模式"),
    "Social Media Analyst": ("💬", "情绪分析师", "扫描 Reddit、StockTwits，量化市场情绪"),
    "News Analyst": ("📰", "新闻分析师", "追踪宏观新闻与公司公告，评估事件冲击"),
    "Fundamentals Analyst": ("📊", "基本面分析师", "评估财报、盈利、内部交易，挖掘内在价值"),
    "Research": ("🔬", "研究团队", "多空双方结构化辩论，寻找逻辑平衡"),
    "Trader": ("💰", "交易员", "汇总所有报告，决定最佳交易时机与规模"),
    "Risk Management": ("🛡️", "风控经理", "全局多维度风控压力测试"),
    "Portfolio Manager": ("📋", "基金经理", "最终审批交易方案"),
}

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1.1rem; color: #888; margin-bottom: 2rem; }
    .agent-card {
        background: #0e1117; border: 1px solid #333; border-radius: 8px;
        padding: 1rem 1.2rem; margin: 0.6rem 0;
    }
    .agent-card.active { border-color: #4da6ff; border-width: 2px; }
    .agent-card.done { border-color: #2ea043; }
    .agent-header { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.4rem; }
    .agent-desc { font-size: 0.85rem; color: #888; }
    .agent-output {
        background: #161b22; border-radius: 6px; padding: 0.8rem;
        margin-top: 0.5rem; font-size: 0.85rem; max-height: 400px;
        overflow-y: auto; white-space: pre-wrap; word-wrap: break-word;
    }
    .decision-box {
        border-radius: 12px; padding: 1.5rem; margin: 1rem 0;
        text-align: center; font-size: 1.3rem;
    }
    .decision-hold { background: #2d2d0f; border: 2px solid #888800; }
    .decision-buy { background: #0f2d0f; border: 2px solid #008800; }
    .decision-sell { background: #2d0f0f; border: 2px solid #880000; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 智能投研分析系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">7 位 AI 分析师协作 · 基本面 / 技术面 / 情绪面 / 新闻面 · 多空辩论 · 风控审批</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    ticker = st.text_input("股票代码", value="AAPL", placeholder="输入美股代码，如 AAPL、NVDA、TSLA")
with col2:
    analysis_date = st.date_input("分析日期", value=datetime.now() - timedelta(days=1))

st.markdown("**热门股票：**" + "　".join(
    f"`{code}` {name}" for code, name in POPULAR_TICKERS.items()
))

with st.expander("⚙️ 高级设置", expanded=False):
    adv_col1, adv_col2 = st.columns(2)
    with adv_col1:
        debate_rounds = st.slider("辩论轮数", 1, 3, 1)
        risk_rounds = st.slider("风控讨论轮数", 1, 3, 1)
    with adv_col2:
        output_lang = st.selectbox("报告语言", ["Chinese", "English"], index=0)


class StreamCapture(io.TextIOBase):
    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.buffer = []

    def write(self, text):
        if text:
            self.buffer.append(text)
            self.log_queue.put(("log", text))
        return len(text) if text else 0

    def flush(self):
        pass

    def get_all(self):
        return "".join(self.buffer)


def detect_agent(line):
    task_match = re.search(r"During task with name '([^']+)'", line)
    if task_match:
        return task_match.group(1)
    for key in AGENT_LABELS:
        if key.lower() in line.lower():
            return key
    return None


def run_analysis(ticker_symbol, date_str, config_overrides, result_queue, log_queue):
    capture = StreamCapture(log_queue)
    old_stdout = sys.stdout
    sys.stdout = capture

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openrouter"
        config["deep_think_llm"] = "LongCat-2.0-Preview"
        config["quick_think_llm"] = "LongCat-2.0-Preview"
        config["backend_url"] = "https://api.longcat.chat/openai/v1"
        config["max_debate_rounds"] = config_overrides.get("debate_rounds", 1)
        config["max_risk_discuss_rounds"] = config_overrides.get("risk_rounds", 1)
        config["output_language"] = config_overrides.get("output_lang", "Chinese")

        ta = TradingAgentsGraph(debug=True, config=config)
        _, decision = ta.propagate(ticker_symbol, date_str)

        result_queue.put(("success", decision, capture.get_all()))

    except Exception as e:
        result_queue.put(("error", str(e), capture.get_all()))
    finally:
        sys.stdout = old_stdout


if st.button("🚀 开始分析", type="primary", use_container_width=True):
    if not ticker.strip():
        st.error("请输入股票代码")
    else:
        ticker_upper = ticker.strip().upper()
        date_str = analysis_date.strftime("%Y-%m-%d")
        ticker_name = POPULAR_TICKERS.get(ticker_upper, ticker_upper)

        result_queue = queue.Queue()
        log_queue = queue.Queue()

        config_overrides = {
            "debate_rounds": debate_rounds,
            "risk_rounds": risk_rounds,
            "output_lang": output_lang,
        }

        thread = threading.Thread(
            target=run_analysis,
            args=(ticker_upper, date_str, config_overrides, result_queue, log_queue),
            daemon=True,
        )
        thread.start()

        st.divider()
        st.markdown(f"### 🔄 正在分析 **{ticker_upper}**（{ticker_name}）")

        progress_bar = st.progress(0)

        agent_order = list(AGENT_LABELS.keys())
        current_agent = None
        agent_outputs = {k: [] for k in agent_order}
        completed_agents = set()
        all_lines = []

        status_container = st.container()
        live_feed = st.empty()
        result_container = st.empty()

        finished = False
        start_time = time.time()

        while not finished:
            new_logs = []
            while True:
                try:
                    msg_type, msg_data = log_queue.get_nowait()
                    if msg_type == "log":
                        new_logs.append(msg_data)
                except queue.Empty:
                    break

            if new_logs:
                for log_text in new_logs:
                    all_lines.append(log_text)
                    detected = detect_agent(log_text)
                    if detected and detected in AGENT_LABELS:
                        if current_agent and current_agent != detected:
                            completed_agents.add(current_agent)
                        current_agent = detected

                    if current_agent:
                        agent_outputs[current_agent].append(log_text)

                progress = min(len(completed_agents) / len(agent_order) * 100, 95)
                progress_bar.progress(int(progress))

                with live_feed.container():
                    elapsed = time.time() - start_time
                    st.caption(f"⏱️ 已运行 {int(elapsed)} 秒")

                    for agent_key in agent_order:
                        icon, label, desc = AGENT_LABELS[agent_key]
                        output_text = "".join(agent_outputs[agent_key])

                        if agent_key in completed_agents:
                            status_icon = "✅"
                            border_class = "done"
                        elif agent_key == current_agent:
                            status_icon = "⏳"
                            border_class = "active"
                        else:
                            status_icon = "⬜"
                            border_class = ""
                            continue

                        with st.expander(
                            f"{status_icon} {icon} {label} — {desc}",
                            expanded=(agent_key == current_agent),
                        ):
                            if output_text.strip():
                                display_text = output_text.strip()
                                if len(display_text) > 3000:
                                    display_text = display_text[:1500] + "\n\n... (中间省略) ...\n\n" + display_text[-1500:]
                                st.markdown(display_text)
                            else:
                                st.caption("等待分析结果...")

            try:
                result_type, *result_data = result_queue.get_nowait()
                finished = True

                if current_agent:
                    completed_agents.add(current_agent)
                progress_bar.progress(100)

                if result_type == "success":
                    decision, full_output = result_data
                    elapsed = time.time() - start_time

                    with result_container.container():
                        st.divider()
                        st.markdown(f"### ⏱️ 分析完成，耗时 {int(elapsed)} 秒")

                        decision_str = decision if isinstance(decision, str) else str(decision)
                        decision_lower = decision_str.lower()

                        if "buy" in decision_lower:
                            icon, label = "🟢", "买入 BUY"
                            st.success(f"## {icon} 最终决策：{label}")
                        elif "sell" in decision_lower:
                            icon, label = "🔴", "卖出 SELL"
                            st.error(f"## {icon} 最终决策：{label}")
                        else:
                            icon, label = "🟡", "持有 HOLD"
                            st.warning(f"## {icon} 最终决策：{label}")

                        reasoning_match = re.search(
                            r'\*\*Reasoning\*\*:\s*(.+?)(?=\n\*\*|\nFINAL|\Z)',
                            full_output, re.DOTALL
                        )
                        stoploss_match = re.search(r'\*\*Stop Loss\*\*:\s*([\d.]+)', full_output)

                        if reasoning_match:
                            st.markdown("#### 📝 决策理由")
                            st.markdown(reasoning_match.group(1).strip())

                        if stoploss_match:
                            st.metric("🎯 止损位", f"${stoploss_match.group(1)}")

                        st.divider()
                        with st.expander("📄 查看完整分析报告", expanded=False):
                            st.markdown(full_output)

                elif result_type == "error":
                    error_msg, full_output = result_data
                    with result_container.container():
                        st.error(f"❌ 分析出错：{error_msg}")
                        with st.expander("错误详情"):
                            st.code(full_output[-2000:] if len(full_output) > 2000 else full_output)

            except queue.Empty:
                pass

            if not finished:
                time.sleep(1)

st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.85rem; padding: 1rem 0;">
    ⚠️ 免责声明：本系统仅供学习交流，所有输出为 AI 辅助参考，不构成投资建议。<br>
    基于 <a href="https://github.com/TauricResearch/TradingAgents" target="_blank">TradingAgents</a>
    （加州大学 & MIT 联合研究）· 多智能体 LLM 金融交易框架
</div>
""", unsafe_allow_html=True)
