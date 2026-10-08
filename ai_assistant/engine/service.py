import time
import json
from ai_assistant.engine.llm import LLMClient
from ai_assistant.engine.prompts import (
    BREAKDOWN_PROMPT_TEMPLATE, RISKS_PROMPT_TEMPLATE,
    WEEKLY_PROMPT_TEMPLATE, QUESTIONS_PROMPT_TEMPLATE, CHAT_PROMPT_TEMPLATE
)
from ai_assistant.engine.schemas import BreakdownOut, RisksOut, WeeklyOut, QuestionsOut, ChatOut
from ai_assistant.engine.parse import parse_and_validate
from ai_assistant.engine.rules import (
    calculate_metrics, generate_fallback_breakdown,
    generate_fallback_weekly, generate_fallback_questions, generate_fallback_chat
)

def run_task(prompt_type: str, facts: dict, user_message: str = "") -> dict:
    """
    Main engine entry point for running AI tasks.
    Returns standard Result dictionary:
    {
       'status': 'SUCCESS' | 'FALLBACK' | 'ERROR',
       'source': 'llm' | 'rules',
       'provider': str,
       'model': str,
       'latency_ms': int,
       'tokens_in': int,
       'tokens_out': int,
       'warnings': list,
       'data': dict,
       'error': str
    }
    """
    start_time = time.time()
    llm = LLMClient()
    metrics = calculate_metrics(facts)
    facts['metrics'] = metrics

    result = {
        'status': 'FALLBACK',
        'source': 'rules',
        'provider': llm.provider,
        'model': llm.model,
        'latency_ms': 0,
        'tokens_in': 0,
        'tokens_out': 0,
        'warnings': [],
        'data': {},
        'error': ''
    }

    schema_map = {
        'breakdown': (BREAKDOWN_PROMPT_TEMPLATE, BreakdownOut, generate_fallback_breakdown),
        'risks': (RISKS_PROMPT_TEMPLATE, RisksOut, lambda f: {'summary': f"Phân tích rủi ro dựa trên dữ liệu hệ thống (Điểm: {f['metrics']['risk_score']}/100)", 'risks': f['metrics']['risks']}),
        'weekly': (WEEKLY_PROMPT_TEMPLATE, WeeklyOut, generate_fallback_weekly),
        'questions': (QUESTIONS_PROMPT_TEMPLATE, QuestionsOut, generate_fallback_questions),
        'chat': (CHAT_PROMPT_TEMPLATE, ChatOut, lambda f: generate_fallback_chat(f, user_message=user_message))
    }

    if prompt_type not in schema_map:
        result['status'] = 'ERROR'
        result['error'] = f"Loại tác vụ không hỗ trợ: {prompt_type}"
        return result

    prompt_tmpl, schema_cls, fallback_fn = schema_map[prompt_type]

    # Check if LLM is configured and operational
    if llm.is_configured():
        try:
            facts_str = json.dumps(facts, ensure_ascii=False, indent=2, default=str)
            if prompt_type == 'chat':
                prompt_text = prompt_tmpl.format(facts_json=facts_str, user_message=user_message)
            else:
                prompt_text = prompt_tmpl.format(facts_json=facts_str)

            raw_resp, t_in, t_out = llm.complete(prompt_text)
            data_dict, warnings = parse_and_validate(raw_resp, schema_cls, facts)

            result['status'] = 'SUCCESS'
            result['source'] = 'llm'
            result['tokens_in'] = t_in
            result['tokens_out'] = t_out
            result['warnings'] = warnings
            result['data'] = data_dict
            result['latency_ms'] = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            result['warnings'].append(f"Không thể gọi dịch vụ LLM: {str(e)}")
            result['error'] = str(e)

    # Fallback to rules-based generation
    fallback_data = fallback_fn(facts)
    result['status'] = 'FALLBACK'
    result['source'] = 'rules'
    result['data'] = fallback_data
    result['latency_ms'] = int((time.time() - start_time) * 1000)

    return result
