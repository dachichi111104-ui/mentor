import json
import re
from pydantic import ValidationError

def extract_json_block(text: str) -> str:
    """
    Extracts valid JSON string from raw markdown text or code blocks.
    """
    if not text:
        return ""
    text = text.strip()

    # Remove markdown ```json ... ``` wrappers
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Find first { or [ and matching last } or ]
    start_brace = text.find('{')
    start_bracket = text.find('[')
    
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        end_brace = text.rfind('}')
        if end_brace != -1:
            return text[start_brace:end_brace+1]
    elif start_bracket != -1:
        end_bracket = text.rfind(']')
        if end_bracket != -1:
            return text[start_bracket:end_bracket+1]

    return text

def parse_and_validate(raw_text: str, schema_cls, facts: dict):
    """
    Parses raw_text to JSON, validates with schema_cls, and filters hallucinated IDs not present in facts.
    Returns tuple (validated_data_dict, warnings_list) or raises ValueError/ValidationError on failure.
    """
    clean_json_str = extract_json_block(raw_text)
    data = json.loads(clean_json_str)

    validated_obj = schema_cls.model_validate(data)
    validated_dict = validated_obj.model_dump()

    warnings = []

    # Filter hallucinated IDs
    valid_task_ids = set()
    valid_milestone_ids = set()

    if 'tasks' in facts:
        for tlist in facts['tasks'].values():
            if isinstance(tlist, list):
                for item in tlist:
                    if isinstance(item, dict) and 'id' in item:
                        valid_task_ids.add(item['id'])
    if 'milestones' in facts and isinstance(facts['milestones'], list):
        for m in facts['milestones']:
            if isinstance(m, dict) and 'id' in m:
                valid_milestone_ids.add(m['id'])

    # Sanitize tasks / risks / questions IDs if needed
    if 'tasks' in validated_dict and isinstance(validated_dict['tasks'], list):
        for task in validated_dict['tasks']:
            if task.get('milestone_id') and task['milestone_id'] not in valid_milestone_ids:
                warnings.append(f"Bỏ milestone_id {task['milestone_id']} không tồn tại trong đồ án")
                task['milestone_id'] = None

    if 'risks' in validated_dict and isinstance(validated_dict['risks'], list):
        for risk in validated_dict['risks']:
            if risk.get('task_id') and risk['task_id'] not in valid_task_ids:
                warnings.append(f"Bỏ task_id {risk['task_id']} không tồn tại khỏi rủi ro")
                risk['task_id'] = None
            if risk.get('milestone_id') and risk['milestone_id'] not in valid_milestone_ids:
                warnings.append(f"Bỏ milestone_id {risk['milestone_id']} không tồn tại khỏi rủi ro")
                risk['milestone_id'] = None

    if 'questions' in validated_dict and isinstance(validated_dict['questions'], list):
        for q in validated_dict['questions']:
            if q.get('related_task_id') and q['related_task_id'] not in valid_task_ids:
                warnings.append(f"Bỏ related_task_id {q['related_task_id']} không tồn tại khỏi câu hỏi")
                q['related_task_id'] = None

    return validated_dict, warnings
