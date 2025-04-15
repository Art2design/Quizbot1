import json

with open('data/demo_ux_ui_content.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for i, q in enumerate(data['themes']['ux_ui_basics']['questions']):
    print(f"{i+1}. {q['id']}: {q['question'][:100]}...")
    print(f"   Correct answer: {q['correct_answer']}")
    print(f"   Answer: {q['options'][q['correct_answer']]}")
    print()