"""Клиент для работы с OpenRouter API"""
import os
import requests
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class OpenRouterClient:
    """Клиент для OpenRouter API"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не установлен")
        
        self.model = model or os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def analyze_news(self, headline: str, content: str) -> Dict:
        """
        Анализирует новость и возвращает hotness и тикеры
        
        Returns:
            {
                'hotness': float (0-1),
                'tickers': List[str],
                'reasoning': str
            }
        """
        
        prompt = f"""Ты - строгий финансовый аналитик. Оцени новость по многофакторной формуле hotness для финансовых рынков.

ЗАГОЛОВОК: {headline}
ТЕКСТ: {content[:2000]}

ФОРМУЛА HOTNESS (0.00 - 1.00):
hotness = scale × market_impact + urgency + novelty + materiality

ГДЕ КАЖДЫЙ КОМПОНЕНТ:

1) SCALE (масштаб события) — вес 0-0.30:
   • 0.30: Глобальное (мировая война, крах G7 экономики, дефолт США/Китая)
   • 0.20-0.25: Национальное (решение ЦБ/ФРС по ставке, смена президента, крупнейшие IPO >$10B)
   • 0.10-0.15: Региональное/Секторное (отраслевое регулирование, слияние крупных компаний)
   • 0.05-0.10: Корпоративное (квартальные отчёты топ-100, M&A средних компаний)
   • 0.00-0.05: Локальное/незначительное

2) MARKET_IMPACT (прямое влияние на рынки) — вес 0-0.30:
   • 0.30: Немедленное (санкции на целую отрасль, дефолт, банкротство Fortune 500)
   • 0.20-0.25: Среднесрочное прямое (изменение ставок, новые налоги, тарифы)
   • 0.10-0.15: Косвенное (регуляторные изменения, отраслевые тренды, прогнозы аналитиков)
   • 0.05-0.10: Слабое косвенное (общие макро-новости, планы без деталей)
   • 0.00-0.05: Минимальное/нет

3) URGENCY (срочность реакции) — вес 0-0.20:
   • 0.20: Требует НЕМЕДЛЕННОЙ реакции (circuit breaker, halt торгов, экстренные события)
   • 0.15: Важно в ближайшие часы (breaking news с ценовым эффектом)
   • 0.10: Актуально сегодня (свежие данные, важные заявления)
   • 0.05: В течение недели (плановые события, анонсы)
   • 0.00: Не срочно (исторические обзоры, долгосрочные планы)

4) NOVELTY (новизна/уникальность) — вес 0-0.20:
   • 0.20: Беспрецедентное (первое в истории, революционное)
   • 0.15: Редкое (раз в 5+ лет: кризисы, мега-сделки)
   • 0.10: Нечастое (раз в год: крупные IPO, смена руководства ЦБ)
   • 0.05: Периодическое (ежеквартально: отчёты, дивиденды)
   • 0.00: Рутинное (ежедневные новости)

5) MATERIALITY (материальность/конкретика активов) — вес 0-0.10:
   • 0.10: Названы конкретные компании/тикеры с цифрами (выручка, цены, объёмы)
   • 0.07: Названы компании без цифр или сектор с цифрами
   • 0.05: Общий сектор/рынок без деталей
   • 0.02: Упоминаются рынки косвенно
   • 0.00: Нет упоминания активов

ФИЛЬТР РЕЛЕВАНТНОСТИ:
Если новость НЕ о финансах/экономике/рынках (спорт, погода, криминал, развлечения, бытовое), установи:
• hotness = 0.00–0.10 (сумма всех компонентов должна быть близка к нулю)
• tickers = []
• reasoning = "Не релевантно для финансовых рынков"

ИЗВЛЕЧЕНИЕ ТИКЕРОВ:
Найди ВСЕ упомянутые финансовые инструменты:
• Акции: AAPL, TSLA, SBER, GAZP, NVDA
• Криптовалюты: BTC, ETH, SOL
• Индексы: S&P500, MOEX, NASDAQ, Dow
• Валюты/Страны: USD, EUR, RU, USA, CN, EU
• Сырьё: GOLD, OIL, GAS

КРИТИЧЕСКИ ВАЖНО ПРО ТОЧНОСТЬ:
• КАЖДАЯ новость УНИКАЛЬНА → hotness ДОЛЖЕН различаться! НЕ используй одинаковые оценки!
• Используй ТОЧНЫЕ значения с 3 знаками после запятой: 0.234, 0.567, 0.891
• ЗАПРЕЩЕНО округлять до 0.25, 0.60, 0.90, 0.67, 0.70!
• Оценивай каждый компонент СТРОГО по критериям - не подгоняй под "красивое" число
• Сумма всех 5 компонентов = итоговый hotness (считай точно, до третьего знака!)

ПРИМЕРЫ ПРАВИЛЬНОЙ РАЗЛИЧАЮЩЕЙСЯ ОЦЕНКИ:
• "Пенсии в РФ должны быть 45К": 0.147 = 0.082+0.031+0.018+0.005+0.011
• "Биткоин >$120K впервые с августа": 0.583 = 0.152+0.218+0.121+0.079+0.013
• "ЦБ РФ повысил ставку до 21%": 0.821 = 0.234+0.271+0.184+0.108+0.024
• "Обзор рынка, общие тренды": 0.089 = 0.041+0.019+0.011+0.000+0.018
• "Новый CEO назначен в среднюю компанию": 0.213 = 0.091+0.057+0.033+0.026+0.006

СТРОГОЕ ТРЕБОВАНИЕ:
Если две новости похожи по важности - всё равно дай им РАЗНЫЕ оценки (точность до 0.001)!

ОТВЕТ (ТОЛЬКО JSON, БЕЗ ТЕКСТА):
{{
    "hotness": 0.583,
    "tickers": ["BTC", "USD"],
    "reasoning": "scale=0.152, market_impact=0.218, urgency=0.121, novelty=0.079, materiality=0.013"
}}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,  # Повышаем для большей вариативности оценок
            "max_tokens": 500,
            "top_p": 0.95  # Увеличиваем для разнообразия
        }
        
        max_retries = 2  # Повторить до 2 раз при пустых ответах
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                # Детальная обработка ошибок
                if response.status_code == 403:
                    error_msg = response.json() if response.content else {}
                    print(f"\n❌ Ошибка 403 Forbidden:")
                    print(f"   Возможные причины:")
                    print(f"   1. Неверный API ключ")
                    print(f"   2. Недостаточно средств на балансе")
                    print(f"   3. API ключ не активирован")
                    print(f"   Детали: {error_msg}")
                    raise ValueError(f"API ключ недействителен: {error_msg}")
                
                if response.status_code == 429:
                    print(f"\n⚠️ Превышен лимит запросов. Подождите...")
                    raise ValueError("Rate limit exceeded")
                
                response.raise_for_status()
                result = response.json()
                raw_content = result['choices'][0]['message']['content']
                
                # Проверка на пустой ответ ДО обработки
                if not raw_content or not raw_content.strip():
                    if attempt < max_retries - 1:
                        print(f"⚠️ Попытка {attempt + 1}/{max_retries}: LLM вернула пустой ответ, повторяю...")
                        import time
                        time.sleep(1)
                        continue
                    else:
                        print(f"❌ LLM вернула пустой ответ после {max_retries} попыток!")
                        print(f"  Модель: {self.model}")
                        print(f"  Заголовок: {headline[:50]}...")
                        return {'hotness': 0.0, 'tickers': [], 'reasoning': 'Пустой ответ от LLM'}
                
                # Агрессивное извлечение JSON из ответа
                import re
                content = raw_content
                
                # 1. Убираем markdown блоки
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                # 2. Ищем последний JSON объект в тексте (самый полный)
                # Используем более точную регулярку для вложенных объектов
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                all_matches = list(re.finditer(json_pattern, content, re.DOTALL))
                
                if all_matches:
                    # Берём последний (обычно самый полный) JSON объект
                    content = all_matches[-1].group(0)
                else:
                    # Если regex не нашёл, пробуем найти вручную от последней { до }
                    start = content.rfind('{')
                    end = content.rfind('}')
                    if start != -1 and end != -1 and start < end:
                        content = content[start:end+1]
                    else:
                        # Вообще не нашли JSON
                        print(f"⚠️ Не удалось найти JSON в ответе!")
                        print(f"  Полный ответ: {raw_content[:300]}")
                        return {'hotness': 0.0, 'tickers': [], 'reasoning': 'JSON не найден в ответе'}
                
                # 3. Очищаем от возможных проблем
                content = content.strip()
                
                # Проверяем, что контент не пустой
                if not content or len(content) < 10:
                    print(f"⚠️ Пустой или слишком короткий JSON после обработки")
                    print(f"  Исходный ответ: {raw_content[:300]}")
                    print(f"  После обработки: {content}")
                    return {'hotness': 0.0, 'tickers': [], 'reasoning': 'Слишком короткий JSON'}
                
                # Парсим JSON
                try:
                    analysis = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Не удалось распарсить JSON: {e}")
                    print(f"Извлечённый JSON: {content[:200]}")
                    return {'hotness': 0.0, 'tickers': [], 'reasoning': 'Ошибка парсинга JSON'}
                
                # Валидация
                hotness = float(analysis.get('hotness', 0.5))
                hotness = max(0.0, min(1.0, hotness))  # Ограничиваем 0-1
                
                tickers = analysis.get('tickers', [])
                if not isinstance(tickers, list):
                    tickers = []
                
                reasoning = analysis.get('reasoning', '')
                
                # Логируем успешный парсинг с ненулевым hotness
                if hotness > 0.01:
                    print(f"  📊 Распознано: hotness={hotness:.3f}, tickers={tickers}")
                
                return {
                    'hotness': hotness,
                    'tickers': tickers,
                    'reasoning': reasoning  # Добавляем обоснование оценки
                }
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Ошибка API запроса: {e}")
                return {'hotness': 0.0, 'tickers': [], 'reasoning': ''}
            except Exception as e:
                print(f"❌ Неожиданная ошибка: {e}")
                return {'hotness': 0.0, 'tickers': [], 'reasoning': ''}

