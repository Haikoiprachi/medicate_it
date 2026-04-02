import pathlib
import os

os.chdir(r'c:\Users\B K Choudhary\MedTriage_Capstone\backend')
main = pathlib.Path('main.py').read_text(encoding='utf-8')
start = main.index('# ── LangGraph State ────────────────────────────────────────────────────────────')
end = main.index('# ── Request / Response Models ──────────────────────────────────────────────────')
triage_block = main[start:end].strip() + '\n\n'

content = '''import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from privacy import privacy
from llm_client import call_llm_json
from risk_engine import compute_base_score, get_rule_based_analysis

''' + triage_block + 'triage_graph = build_triage_graph()\n'
pathlib.Path('triage_engine.py').write_text(content, encoding='utf-8')
print('triage_engine.py rewritten with agent logic block.')
