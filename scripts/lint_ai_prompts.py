import os
import sys

def lint_ai_prompts():
    print("Checking AI prompt templates for ground-truth facts enforcement...")
    prompt_file = os.path.join('ai_assistant', 'engine', 'prompts.py')
    if not os.path.exists(prompt_file):
        print(f"ERROR: {prompt_file} not found.")
        return 1

    with open(prompt_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if '{facts_json}' not in content:
            print("LINT ERROR: Prompt templates must inject {facts_json}.")
            return 1

    print("OK — Analyzed AI prompt templates, 0 errors.")
    return 0

if __name__ == '__main__':
    sys.exit(lint_ai_prompts())
