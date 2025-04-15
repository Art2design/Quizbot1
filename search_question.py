import json

with open('data/demo_ux_ui_content.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

any_match = False
for q in data['themes']['ux_ui_basics']['questions']:
    if 'принцип эмпатии' in q['question']:
        print(json.dumps(q, ensure_ascii=False, indent=2))
        any_match = True

if not any_match:
    print('Вопрос не найден')