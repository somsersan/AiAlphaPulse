"""Анализатор новостей для генерации детальной информации через LLM"""
import json
from typing import Dict
from ..llm.openrouter_client import OpenRouterClient


class NewsAnalyzer:
    """Генерирует детальную аналитику по новости"""
    
    def __init__(self, api_key: str = None, model: str = "mistralai/mistral-7b-instruct"):
        self.llm_client = OpenRouterClient(api_key=api_key, model=model)
    
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
            "model": self.llm_client.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 800
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
            
            # Извлекаем JSON
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            analysis = json.loads(content.strip())
            return analysis
            
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

2. draft (структурированный текст):
   - Заголовок (1 строка)
   - Лид-абзац (2-3 предложения с главной сутью)
   - 3 ключевых пункта (буллеты)
   - Заключение/контекст (1-2 предложения)

Ответь ТОЛЬКО в JSON формате:
{{
    "why_now": "Объяснение актуальности",
    "draft": "Заголовок\\n\\nЛид-абзац...\\n\\n• Пункт 1\\n• Пункт 2\\n• Пункт 3\\n\\nЗаключение"
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

2. draft (детальный анализ):
   - Заголовок с эмодзи 🔥
   - Лид-абзац с ключевой сутью
   - 3 главных последствия (буллеты)
   - Влияние на рынки

3. trading_signal (конкретные рекомендации):
   - Направление (BUY/SELL/HOLD)
   - Затронутые активы
   - Временной горизонт
   - Риски

Ответь ТОЛЬКО в JSON формате:
{{
    "why_now": "Критическая важность новости",
    "draft": "🔥 Заголовок\\n\\nСуть...\\n\\n• Последствие 1\\n• Последствие 2\\n• Последствие 3\\n\\nВлияние на рынки",
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

