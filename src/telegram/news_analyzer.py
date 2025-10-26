"""Анализатор новостей для генерации детальной информации через LLM"""
import json
import os
from typing import Dict
from ..llm.openrouter_client import OpenRouterClient


class NewsAnalyzer:
    """Генерирует детальную аналитику по новости"""
    
    def __init__(self, api_key: str = None, model: str = None):
        # Для детального анализа используем более мощную модель
        # LLM_ANALYSIS_MODEL - для детального анализа (по умолчанию Claude 3.5 Sonnet)
        # LLM_MODEL - для быстрой оценки hotness
        self.analysis_model = model or os.getenv("LLM_ANALYSIS_MODEL", "anthropic/claude-3.5-sonnet")
        self.llm_client = OpenRouterClient(api_key=api_key, model=self.analysis_model)
    
    def generate_full_analysis(self, news: Dict) -> Dict:
        """
        Генерирует полный анализ новости в формате аналитической карточки
        
        Args:
            news: словарь с headline, content, tickers, hotness, urls, published_at, source
            
        Returns:
            {
                'analysis_text': str - готовая карточка в формате Markdown
            }
        """
        
        headline = news.get('headline', '')
        content = news.get('content', '')
        tickers = news.get('tickers', [])
        hotness = news.get('hotness', 0)
        urls = news.get('urls', [])
        published_at = news.get('published_at', '')
        source = news.get('source', 'Неизвестный источник')
        
        # Формируем промпт для генерации аналитической карточки
        prompt = self._create_analysis_card_prompt(headline, content, tickers, hotness, urls, published_at, source)
        
        headers = {
            "Authorization": f"Bearer {self.llm_client.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.analysis_model,  # Используем мощную модель
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Более низкая температура для точного анализа
            "max_tokens": 1500  # Больше токенов для детального анализа
        }
        
        try:
            import requests
            response = requests.post(
                self.llm_client.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return self._get_fallback_analysis(hotness)
            
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Нормализуем ответ модели: убираем markdown-ограждения и вытаскиваем JSON
            import re
            raw_content = content or ""
            if "```json" in raw_content:
                try:
                    content = raw_content.split("```json", 1)[1].split("```", 1)[0]
                except Exception:
                    content = raw_content
            elif "```" in raw_content:
                try:
                    content = raw_content.split("```", 1)[1].split("```", 1)[0]
                except Exception:
                    content = raw_content
            else:
                content = raw_content

            # Извлекаем JSON подстроку по внешним фигурным скобкам
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            # Удаляем проблемные управляющие символы, сохраняя переносы строк
            def _sanitize(s: str) -> str:
                if not isinstance(s, str):
                    return s
                # Убираем BOM и нулевые байты/вертикальные табы/форм-фиды
                s = s.replace('\ufeff', '')
                s = s.replace('\x00', '').replace('\x0b', ' ').replace('\x0c', ' ')
                return s

            content = _sanitize(content)

            # Проверяем, что после всех обработок остался валидный контент
            if not content or not content.strip():
                print(f"⚠️ Ошибка генерации анализа: пустой ответ от LLM")
                return self._get_fallback_analysis(hotness, urls, published_at, source)

            # Парсим JSON, разрешая неэкранированные управляющие символы внутри строк
            analysis = json.loads(content.strip(), strict=False)
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка генерации анализа: невалидный JSON - {e}")
            print(f"Полученный ответ: {content if 'content' in locals() else 'N/A'}")
            return self._get_fallback_analysis(hotness, urls, published_at, source)
        except Exception as e:
            print(f"⚠️ Ошибка генерации анализа: {e}")
            return self._get_fallback_analysis(hotness, urls, published_at, source)
    
    def _create_analysis_card_prompt(self, headline: str, content: str, tickers: list, hotness: float, urls: list, published_at: str, source: str) -> str:
        """Промпт для генерации аналитической карточки новости"""
        tickers_str = ', '.join(tickers) if tickers else '—'
        url_str = urls[0] if urls else 'нет ссылки'
        
        # Определяем язык на основе заголовка
        is_russian = any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in headline)
        lang_instruction = "на русском языке" if is_russian else "in English"
        
        return f"""Ты — агент аналитики финансовых новостей для Telegram-бота AI ALPHA PULSE. Твоя задача — создать компактную, объяснимую аналитическую карточку {lang_instruction}.

ВХОДНЫЕ ДАННЫЕ:
Заголовок: {headline}
Текст: {content[:2000]}
Тикеры: {tickers_str}
Источник: {source}
Время публикации: {published_at}
URL: {url_str}
Hotness score: {hotness:.2f}

ТРЕБОВАНИЯ К ВЫВОДУ:
Создай аналитическую карточку в формате Markdown (Telegram-совместимом). Язык карточки: {lang_instruction}.

ОБЯЗАТЕЛЬНЫЕ ПОЛЯ (строго в этом порядке):

1. TL;DR (20-30 слов): Суть новости и её влияние на рынки/активы
2. Ключевые факты (2-4 пункта): Конкретные факты из текста, без домыслов
3. Затронутые активы: Список тикеров через запятую или "—"
4. Sentiment score: Число от -1 до 1 и краткое объяснение (почему позитивный/негативный/нейтральный)
5. News score: Число от 0 до 1 и основные драйверы (sentiment / mentions / authority)
6. Рекомендация: "Monitor" / "Bullish (consider buy)" / "Bearish (consider sell)" / "No action" + объяснение 1-2 предложения
7. Confidence: "Low" / "Medium" / "High" + обоснование (почему такая уверенность)

СТИЛЬ:
- Кратко, нейтрально, делово. Максимум 700 символов
- Используй формулировки: "consider", "monitor", "may indicate" (не давай прямых финансовых советов)
- Если данных недостаточно — укажи это в Confidence и TL;DR
- Не придумывай статистику, если её нет в тексте
- Используй эмодзи там, где уместно

Ответь ТОЛЬКО в JSON формате:
{{
    "analysis_text": "🔎 *TL;DR:* ...\\n\\n📌 *Ключевые факты:*\\n• Факт 1\\n• Факт 2\\n• Факт 3\\n\\n📈 *Затронутые активы:* ...\\n💡 *Sentiment:* ... — ...\\n⭐ *News score:* ... — драйверы: ...\\n\\n🧭 *Рекомендация:* ... — ...\\n🔒 *Confidence:* ... — ...\\n\\n🔗 {url_str}"
}}

ВАЖНО: Весь текст карточки должен быть в одной строке analysis_text с экранированными переносами строк (\\n). Используй Markdown-форматирование (*жирный текст*) для заголовков полей."""
    
    def _get_fallback_analysis(self, hotness: float, urls: list, published_at: str, source: str) -> Dict:
        """Запасной анализ при ошибке LLM"""
        url_str = urls[0] if urls else 'нет ссылки'
        
        fallback_text = f"""🔎 *TL;DR:* Анализ временно недоступен — ошибка обработки LLM.

📌 *Ключевые факты:*
• Новость требует ручного анализа
• Автоматическая обработка завершилась с ошибкой

📈 *Затронутые активы:* —
💡 *Sentiment:* 0.0 — не определён
⭐ *News score:* {hotness:.2f} — базовая оценка hotness

🧭 *Рекомендация:* Monitor — требуется дополнительный анализ
🔒 *Confidence:* Low — автоматический анализ недоступен

🔗 {url_str}"""
        
        return {
            'analysis_text': fallback_text
        }

