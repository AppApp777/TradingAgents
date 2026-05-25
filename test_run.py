from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["deep_think_llm"] = "deepseek-v4-flash"
config["quick_think_llm"] = "deepseek-v4-flash"
config["backend_url"] = "https://api.b.ai/v1"
config["max_debate_rounds"] = 1
config["max_risk_discuss_rounds"] = 1
config["output_language"] = "Chinese"

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("AAPL", "2026-05-23")
print("\n" + "="*60)
print("FINAL DECISION:")
print("="*60)
print(decision)
