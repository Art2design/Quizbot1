import json
import re

# Загрузка контента
with open('data/ux_ui_content.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Находим вопросы
questions = []
for theme in data['themes']:
    if 'questions' in theme:
        questions.extend(theme['questions'])

# Функция для сокращения длинных вариантов ответов
def shorten_option(option, max_length=40):
    if len(option) <= max_length:
        return option
    
    # Пытаемся сократить, удаляя некоторые общие фразы и слова
    # Удаляем вводные фразы
    shortenings = [
        (r'Дизайнер (использует|применяет|создаёт|выбирает|разрабатывает) ', ''),
        (r'Это (процесс|подход|метод|принцип) ', ''),
        (r'Это ', ''),
        (r'Предложение (Анны|Павла|дизайнера), так как ', ''),
        (r' для того, чтобы', ''),
        (r' для того чтобы', ''),
        (r' потому что', ''),
        (r', так как', ':'),
        (r' с целью', ''),
        (r'с помощью которого', 'где'),
        (r'с помощью которой', 'где'),
        (r'который позволяет', 'позволяющий'),
        (r'которая позволяет', 'позволяющая'),
        (r'именно', ''),
        (r'конкретно', ''),
        (r'специально', ''),
        (r'в основном', ''),
        (r'является', '-'),
    ]
    
    shortened = option
    for pattern, replacement in shortenings:
        shortened = re.sub(pattern, replacement, shortened)
    
    # Если после всех сокращений текст всё ещё слишком длинный
    if len(shortened) > max_length:
        # Пробуем использовать простое сокращение - оставляем только начало
        shortened = shortened[:max_length-3] + '...'
    
    return shortened

# Создаем копию вопросов с сокращенными вариантами ответов
shortened_questions = []

for q in questions:
    # Создаем копию вопроса
    new_q = q.copy()
    
    # Применяем сокращение к каждому варианту ответа
    if 'options' in new_q:
        new_q['options'] = [shorten_option(opt) for opt in new_q['options']]
        
    shortened_questions.append(new_q)

# Вывод статистики
print("Анализ длины вариантов ответов после сокращения:")
original_max_length = max([max([len(opt) for opt in q['options']]) for q in questions if 'options' in q])
shortened_max_length = max([max([len(opt) for opt in q['options']]) for q in shortened_questions if 'options' in q])

print(f"Максимальная длина варианта до сокращения: {original_max_length} символов")
print(f"Максимальная длина варианта после сокращения: {shortened_max_length} символов")

# Вывод примеров
print("\nПримеры сокращения вариантов ответов:")
for original, shortened in zip(questions[:5], shortened_questions[:5]):
    print(f"\nВопрос: {original['question']}")
    print("Оригинальные варианты ответов:")
    for i, opt in enumerate(original['options']):
        print(f"{i+1}. {opt} (длина: {len(opt)} символов)")
    
    print("\nСокращенные варианты ответов:")
    for i, opt in enumerate(shortened['options']):
        print(f"{i+1}. {opt} (длина: {len(opt)} символов)")
    print("-" * 80)

# Подсчет количества вопросов с вариантами ответов короче 40 символов
original_short = sum(1 for q in questions if 'options' in q and max([len(opt) for opt in q['options']]) <= 40)
shortened_short = sum(1 for q in shortened_questions if 'options' in q and max([len(opt) for opt in q['options']]) <= 40)

print(f"\nВопросы с вариантами ответов короче 40 символов до сокращения: {original_short} из {len(questions)} ({original_short/len(questions)*100:.1f}%)")
print(f"Вопросы с вариантами ответов короче 40 символов после сокращения: {shortened_short} из {len(shortened_questions)} ({shortened_short/len(shortened_questions)*100:.1f}%)")