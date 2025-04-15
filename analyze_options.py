import json

# Загрузка контента
with open('data/ux_ui_content.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Попробуем найти вопросы в структуре данных
print("Ключи в JSON файле:", list(data.keys()))

questions = []
# Проверим, есть ли ключ 'general_questions'
if 'general_questions' in data:
    questions.extend(data['general_questions'])
    print(f"Найдено вопросов в 'general_questions': {len(data['general_questions'])}")

# Проверим, есть ли вопросы внутри тем
if 'themes' in data:
    for theme in data['themes']:
        if 'questions' in theme:
            questions.extend(theme['questions'])
            print(f"Найдено вопросов в теме '{theme.get('name', theme.get('id', 'unknown'))}': {len(theme['questions'])}")

short_enough = 0  # Количество вопросов с короткими вариантами ответов
long_options = 0  # Количество вопросов с длинными вариантами ответов
max_option_length = 0  # Максимальная длина варианта ответа

# Считаем варианты ответов для различных пороговых значений
thresholds = [20, 25, 30, 35, 40, 45, 50]
threshold_counts = {t: 0 for t in thresholds}

# Анализ длины вариантов ответов
for q in questions:
    if 'options' in q:
        options_length = max([len(opt) for opt in q['options']])
        max_option_length = max(max_option_length, options_length)
        
        # Подсчет по различным порогам
        for t in thresholds:
            if options_length <= t:
                threshold_counts[t] += 1
        
        if options_length <= 30:
            short_enough += 1
        else:
            long_options += 1

print(f'Всего вопросов: {len(questions)}')
print(f'Вопросы с короткими вариантами ответов (до 30 символов): {short_enough}')
print(f'Вопросы с длинными вариантами ответов (более 30 символов): {long_options}')
print(f'Максимальная длина варианта ответа: {max_option_length} символов')

# Вывод количества вопросов для разных пороговых значений
print("\nАнализ по различным пороговым значениям длины ответов:")
for t in sorted(thresholds):
    percent = (threshold_counts[t] / len(questions)) * 100 if len(questions) > 0 else 0
    print(f"Варианты ответов до {t} символов: {threshold_counts[t]} вопросов ({percent:.1f}%)")

print('\nПримеры длинных вариантов ответов:')
count = 0
for q in questions:
    if 'options' in q:
        options_length = max([len(opt) for opt in q['options']])
        if options_length > 30 and count < 5:
            print(f'\nВопрос: {q["question"]}')
            print('Варианты ответов:')
            for i, opt in enumerate(q['options']):
                print(f'{i+1}. {opt} (длина: {len(opt)} символов)')
            count += 1