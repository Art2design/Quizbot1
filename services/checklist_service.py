from typing import Dict, List, Any
import json
import os
from config import config
from utils.logger import logger

class ChecklistService:
    def __init__(self, use_demo_mode=False):
        # Используем демо-контент или полную версию в зависимости от параметра
        self.content_file = config.demo_content_file if use_demo_mode else config.content_file
        self.is_demo_mode = use_demo_mode
        self.resources_by_tag = self._load_resources()
        
    def _load_resources(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Загружает ресурсы из файла контента
        """
        try:
            with open(self.content_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
                
                # Преобразуем структуру ресурсов в формат resources_by_tag
                resources_by_tag = {}
                
                # Проверяем формат с ресурсами по тегам (новый формат демо)
                if "resources" in content_data and isinstance(content_data["resources"], dict):
                    # Формат: {"resources": {"tag1": [resource1, resource2], "tag2": [resource3]}}
                    for tag, resources_list in content_data["resources"].items():
                        resources_by_tag[tag] = resources_list
                    
                    mode = "demo" if self.is_demo_mode else "full version"
                    logger.info(f"Loaded resources in new format for {mode}")
                    return resources_by_tag
                
                # Проверяем новый формат с секцией resources на верхнем уровне (список ресурсов)
                elif "resources" in content_data and isinstance(content_data["resources"], list):
                    # Новый формат данных с ресурсами на верхнем уровне в виде списка
                    for resource in content_data.get("resources", []):
                        tag = resource.get("tag")
                        if tag:
                            if tag not in resources_by_tag:
                                resources_by_tag[tag] = []
                            resources_by_tag[tag].append(resource)
                    
                    mode = "demo" if self.is_demo_mode else "full version"
                    logger.info(f"Loaded resources in list format for {mode}")
                    return resources_by_tag
                    
                # Старый формат - обрабатываем все темы в файле контента
                for theme in content_data.get("themes", []):
                    # Получаем все ресурсы для темы
                    resources = theme.get("resources", [])
                    
                    # Для каждого ресурса добавляем его в ресурсы по тегам
                    for resource in resources:
                        # Получаем теги ресурса
                        tags = resource.get("tags", [])
                        
                        # Добавляем ресурс в словарь для каждого тега
                        for tag in tags:
                            if tag not in resources_by_tag:
                                resources_by_tag[tag] = []
                            
                            # Добавляем ресурс без поля tags, чтобы не дублировать информацию
                            resource_copy = resource.copy()
                            resource_copy.pop("tags", None)
                            resources_by_tag[tag].append(resource_copy)
                
                # Пишем в лог информацию о загруженных ресурсах
                mode = "demo" if self.is_demo_mode else "full version"
                logger.info(f"Loaded resources in old format for {mode}")
                return resources_by_tag
                
        except FileNotFoundError:
            logger.error(f"Content file not found: {self.content_file}")
            # Пробуем загрузить альтернативный файл, если это демо и он не найден
            if self.is_demo_mode and os.path.exists(config.content_file):
                logger.warning(f"Falling back to full version content file for resources")
                with open(config.content_file, 'r', encoding='utf-8') as f:
                    content_data = json.load(f)
                    # Аналогичный код обработки как выше
                    # ...
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in content file: {self.content_file}")
            return {}
    
    def generate_checklist(self, failed_tags: List[tuple]) -> Dict[str, Any]:
        """
        Генерирует чек-лист ресурсов на основе тегов с ошибками
        
        Args:
            failed_tags: Список кортежей (тег, количество_ошибок)
            
        Returns:
            Dict с двумя полями:
            - resources: список рекомендуемых ресурсов (не более 8)
            - tags_analysis: информация о тегах с ошибками в форматированном виде
        """
        if not failed_tags:
            return {
                "resources": [],
                "tags_analysis": "У вас не было ошибок! Отличный результат!"
            }
        
        # Сортируем теги по количеству ошибок (должны уже быть отсортированы, но для надежности)
        sorted_tags = sorted(failed_tags, key=lambda x: x[1], reverse=True)
        
        # Создаем анализ тегов
        tags_analysis = self._generate_tags_analysis(sorted_tags)
        
        # Отбираем ресурсы
        resources = self._select_resources(sorted_tags)
        
        return {
            "resources": resources,
            "tags_analysis": tags_analysis
        }
    
    def _generate_tags_analysis(self, sorted_tags: List[tuple]) -> str:
        """
        Создает форматированный текст анализа тегов с ошибками
        """
        if not sorted_tags:
            return "У вас не было ошибок! Отличный результат!"
        
        # Группируем теги по количеству ошибок
        tags_by_error_count = {}
        for tag, count in sorted_tags:
            if count not in tags_by_error_count:
                tags_by_error_count[count] = []
            tags_by_error_count[count].append(tag)
        
        # Отсортированные по убыванию количества ошибок
        error_counts = sorted(tags_by_error_count.keys(), reverse=True)
        
        analysis = ""
        
        # Инициализируем переменную с безопасным значением
        max_error_count = 0
        
        # Самые сложные темы (наибольшее количество ошибок)
        if error_counts:
            max_error_count = error_counts[0]
            hardest_tags = tags_by_error_count[max_error_count]
            hardest_tags_str = ", ".join(hardest_tags)
            
            if len(hardest_tags) == 1:
                analysis += f"<b>Самая сложная для вас тема:</b> \"{hardest_tags_str}\"\n\n"
            else:
                analysis += f"<b>Самые сложные для вас темы:</b> \"{hardest_tags_str}\"\n\n"
        
        # Средние по сложности темы
        middle_counts = [count for count in error_counts if count != max_error_count and count > 1]
        if middle_counts:
            middle_tags = []
            for count in middle_counts:
                middle_tags.extend(tags_by_error_count[count])
            
            middle_tags_str = ", ".join(middle_tags)
            analysis += f"<b>Вы также сделали ошибки в темах:</b> \"{middle_tags_str}\"\n\n"
        
        # Темы с одной ошибкой
        if 1 in tags_by_error_count:
            one_error_tags = tags_by_error_count[1]
            one_error_tags_str = ", ".join(one_error_tags)
            
            analysis += f"<b>И немного ошиблись в темах:</b> \"{one_error_tags_str}\"\n\n"
        
        return analysis
    
    def _select_resources(self, sorted_tags: List[tuple]) -> List[Dict[str, str]]:
        """
        Отбирает не более 8 ресурсов, распределяя их пропорционально количеству ошибок по тегам
        """
        if not sorted_tags:
            return []
        
        # Используем ресурсы из единого файла контента
        resources_by_tag = self.resources_by_tag
        
        if not resources_by_tag:
            logger.warning("No resources loaded, unable to generate checklist")
            return []
        
        # Общее количество ошибок
        total_errors = sum(count for _, count in sorted_tags)
        
        # Максимальное количество ресурсов
        max_resources = 8
        
        # Рассчитываем количество ресурсов для каждого тега
        resources_per_tag = {}
        for tag, count in sorted_tags:
            # Пропорционально количеству ошибок определяем количество ресурсов
            tag_resources_count = max(1, round((count / total_errors) * max_resources))
            resources_per_tag[tag] = tag_resources_count
        
        # Корректируем количество ресурсов, если их получается больше 8
        total_resources = sum(resources_per_tag.values())
        if total_resources > max_resources:
            # Если превышен лимит, убираем ресурсы у тегов с наименьшим количеством ошибок
            tags_sorted_by_errors = [tag for tag, _ in sorted_tags]
            for tag in reversed(tags_sorted_by_errors):
                if total_resources <= max_resources:
                    break
                if resources_per_tag[tag] > 1:
                    resources_per_tag[tag] -= 1
                    total_resources -= 1
        
        # Собираем рекомендуемые ресурсы
        selected_resources = []
        
        for tag, resources_count in resources_per_tag.items():
            if tag in resources_by_tag and resources_by_tag[tag]:
                # Берем нужное количество ресурсов для тега
                tag_resources = resources_by_tag[tag]
                # Ограничиваем количество ресурсов для тега
                for resource in tag_resources[:resources_count]:
                    # Убираем "Что даст:" из описания ресурса, если оно есть
                    modified_resource = resource.copy()
                    if 'description' in modified_resource:
                        modified_resource['description'] = modified_resource['description'].replace("Что даст: ", "")
                    selected_resources.append(modified_resource)
            else:
                # Если для тега нет ресурсов, логируем это
                logger.warning(f"No resources found for tag: {tag}")
        
        # Ограничиваем общее количество ресурсов до 8
        return selected_resources[:max_resources]