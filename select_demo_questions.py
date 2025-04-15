import json
import re
import copy

# Загрузка контента
with open('data/ux_ui_content.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Находим вопросы
all_questions = []
for theme in data['themes']:
    if 'questions' in theme:
        theme_questions = copy.deepcopy(theme['questions'])
        # Добавляем информацию о теме к каждому вопросу
        for q in theme_questions:
            q['theme_id'] = theme['id']
            q['theme_name'] = theme['name']
        all_questions.extend(theme_questions)

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

# Оценка вопросов для отбора
scored_questions = []
for q in all_questions:
    # Пропускаем вопросы без вариантов ответов
    if 'options' not in q:
        continue
    
    # Оценка вопроса (начальное значение)
    score = 100
    
    # Проверка длины вариантов ответов
    max_option_length = max([len(opt) for opt in q['options']])
    
    # Если варианты короткие - это хорошо
    if max_option_length <= 30:
        score += 50  # Большой бонус за короткие варианты
    elif max_option_length <= 40:
        score += 25  # Средний бонус за приемлемую длину
    else:
        # Штраф за длинные варианты, пропорциональный длине
        score -= (max_option_length - 40) / 2
    
    # Создаем сокращенные варианты ответов для оценки
    shortened_options = [shorten_option(opt) for opt in q['options']]
    
    # Оценка сокращенных вариантов - насколько они близки к оригиналу
    similarity_score = 0
    for orig, shortened in zip(q['options'], shortened_options):
        if len(orig) <= 40:  # Если оригинал уже короткий
            similarity_score += 1
        else:
            # Проверяем, сколько слов из оригинала сохранилось в сокращенной версии
            orig_words = set(orig.lower().split())
            shortened_words = set(shortened.lower().split())
            common_words = orig_words.intersection(shortened_words)
            
            if len(orig_words) > 0:
                similarity = len(common_words) / len(orig_words)
                similarity_score += similarity
    
    # Нормализуем score_similarity и добавляем к общей оценке
    if len(q['options']) > 0:
        similarity_score = (similarity_score / len(q['options'])) * 30
        score += similarity_score
    
    # Добавляем информацию к вопросу
    q['score'] = score
    q['max_option_length'] = max_option_length
    q['shortened_options'] = shortened_options
    scored_questions.append(q)

# Сортируем вопросы по оценке и отбираем топ-10
selected_questions = sorted(scored_questions, key=lambda x: x['score'], reverse=True)[:10]

# Выводим отобранные вопросы
print("Отобрано 10 наиболее подходящих вопросов:")
for i, q in enumerate(selected_questions, 1):
    print(f"\n{i}. Вопрос: {q['question']} (оценка: {q['score']:.1f})")
    if 'id' in q:
        print(f"   ID: {q['id']}")
    print(f"   Тема: {q.get('theme_name', 'Нет темы')}")
    print(f"   Макс. длина варианта: {q['max_option_length']} символов")
    
    print("   Оригинальные варианты ответов:")
    for j, opt in enumerate(q['options']):
        print(f"     {j+1}. {opt} ({len(opt)} символов)")
    
    print("   Сокращенные варианты ответов:")
    for j, opt in enumerate(q['shortened_options']):
        print(f"     {j+1}. {opt} ({len(opt)} символов)")

# Сохраняем отобранные вопросы в новый JSON файл
output_data = copy.deepcopy(data)

# Очищаем вопросы во всех темах
for theme in output_data['themes']:
    if 'questions' in theme:
        # Сохраняем только те вопросы, которые есть в отобранных 10
        selected_ids = [q['id'] for q in selected_questions if 'id' in q]
        theme['questions'] = [q for q in theme['questions'] if q.get('id') in selected_ids]

# Сохраняем модифицированный файл
with open('data/demo_ux_ui_content.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\nСоздан файл data/demo_ux_ui_content.json с отобранными вопросами")