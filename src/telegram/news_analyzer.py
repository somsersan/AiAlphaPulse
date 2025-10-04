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
        Генерирует полный анализ новости
        
        Args:
            news: словарь с headline, content, tickers, hotness
            
        Returns:
            {
                'why_now': str,
                'draft': str,
                'trading_signal': str (только для hotness >= 0.7)
            }
        """
        
        headline = news.get('headline', '')
        content = news.get('content', '')
        tickers = news.get('tickers', [])
        hotness = news.get('hotness', 0)
        
        # Формируем промпт в зависимости от горячности
        if hotness >= 0.7:
            prompt = self._create_hot_news_prompt(headline, content, tickers, hotness)
        else:
            prompt = self._create_regular_news_prompt(headline, content, tickers, hotness)
        
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
                return self._get_fallback_analysis(hotness)

            # Парсим JSON, разрешая неэкранированные управляющие символы внутри строк
            analysis = json.loads(content.strip(), strict=False)
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка генерации анализа: невалидный JSON - {e}")
            print(f"Полученный ответ: {content if 'content' in locals() else 'N/A'}")
            return self._get_fallback_analysis(hotness)
        except Exception as e:
            print(f"⚠️ Ошибка генерации анализа: {e}")
            return self._get_fallback_analysis(hotness)
    
    def _create_regular_news_prompt(self, headline: str, content: str, tickers: list, hotness: float) -> str:
        """Промпт для обычных новостей"""
        tickers_str = ', '.join(tickers) if tickers else 'не указаны'
        
        return f"""Проанализируй финансовую новость и создай аналитическую справку.

ЗАГОЛОВОК: {headline}
ТЕКСТ: {content[:1500]}
ТИКЕРЫ: {tickers_str}
HOTNESS: {hotness:.2f}

Задачи:
1. why_now (1-2 предложения): Почему эта новость важна СЕЙЧАС? Укажи новизну, актуальность, масштаб влияния.

2. draft (моноширинный структурированный текст для быстрого копирования в Telegram):
   - Используй только текст и переносы строк, без внутреннего Markdown или код-блоков (мы сами обернём результат в код-блок).
   - Структура:
     Заголовок
     \n
     Лид-абзац (2-3 предложения)
     \n
     • Пункт 1
     • Пункт 2
     • Пункт 3
     \n
     Влияние: кратко о влиянии на рынки/активы
     Действие: BUY/SELL/HOLD или «Наблюдать» (если рекомендация неочевидна)

Ответь ТОЛЬКО в JSON формате:
{{
    "why_now": "Объяснение актуальности",
    "draft": "Заголовок\\n\\nЛид-абзац...\\n\\n• Пункт 1\\n• Пункт 2\\n• Пункт 3\\n\\nВлияние: ...\\nДействие: BUY/SELL/HOLD или Наблюдать"
}}"""
    
    def _create_hot_news_prompt(self, headline: str, content: str, tickers: list, hotness: float) -> str:
        """Промпт для горячих новостей (hotness >= 0.7)"""
        tickers_str = ', '.join(tickers) if tickers else 'не указаны'
        
        return f"""🔥 ГОРЯЧАЯ НОВОСТЬ! Проанализируй и дай торговые рекомендации.

ЗАГОЛОВОК: {headline}
ТЕКСТ: {content[:1500]}
ТИКЕРЫ: {tickers_str}
HOTNESS: {hotness:.2f}

Задачи:
1. why_now (1-2 предложения): Почему это КРИТИЧЕСКИ важно сейчас? Укажи срочность и масштаб.

2. draft (моноширинный детальный анализ, без внутреннего markdown, мы сами обернём):
   - Заголовок с эмодзи 🔥 (без разметки)
   - Лид-абзац с ключевой сутью
   - 3 главных последствия (буллеты)
   - Влияние на рынки
   - Действие: BUY/SELL/HOLD или «Наблюдать», с кратким обоснованием

3. trading_signal (конкретные рекомендации):
   - Направление (BUY/SELL/HOLD)
   - Затронутые активы
   - Временной горизонт
   - Риски

Ответь ТОЛЬКО в JSON формате:
{{
    "why_now": "Критическая важность новости",
    "draft": "🔥 Заголовок\\n\\nСуть...\\n\\n• Последствие 1\\n\\n• Последствие 2\\n\\n• Последствие 3\\n\\nВлияние: ...\\nДействие: BUY/SELL/HOLD или Наблюдать",
    "trading_signal": "📊 СИГНАЛ: BUY/SELL/HOLD\\n🎯 Активы: ...\\n⏰ Горизонт: ...\\n⚠️ Риски: ..."
}}"""
    
    def _get_fallback_analysis(self, hotness: float) -> Dict:
        """Запасной анализ при ошибке LLM"""
        base = {
            'why_now': 'Анализ временно недоступен',
            'draft': 'Детальный анализ формируется...'
        }
        
        if hotness >= 0.7:
            base['trading_signal'] = '⚠️ Требуется ручной анализ'
        
        return base

