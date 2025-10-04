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
        
        prompt = f"""Ты - строгий финансовый аналитик и фильтр релевантности. Проанализируй новость и определи её значимость для финансовых рынков.

ЗАГОЛОВОК: {headline}

ТЕКСТ: {content[:2000]}

ИНСТРУКЦИЯ:
1) Сначала ОПРЕДЕЛИ РЕЛЕВАНТНОСТЬ к финансам/рынкам/экономике. Если новости НЕ имеют явной финансовой связи (рынки капитала, компании, отчётности, макроэкономика, регуляторы, санкции, отраслевые факторы, процентные ставки, инфляция, валюты, сырьё и т.п.), установи hotness в диапазоне 0.00–0.10 и верни пустой массив тикеров.
   - НЕрелевантные примеры: спорт, криминал, погода, развлечения, бытовые происшествия, политика без экономического/рыночного эффекта.
   - Пограничные случаи (политика/технологии/соц. темы): снижать hotness до 0.05–0.20, если нет прямой связи с рынками/компаниями/регуляциями/макро.
2) Если релевантна, определи основную суть новости и оцени "горячность" (hotness) от 0.00 до 1.00 по критериям:

   МАСШТАБ СОБЫТИЯ (0-0.30):
   - Глобальное влияние (>0.25): война, мировой кризис, крах крупнейших компаний
   - Национальное влияние (0.15-0.25): решения ЦБ, смена правительства, крупные IPO
   - Региональное/отраслевое (0.05-0.15): локальные события, корпоративные новости
   - Локальное/незначительное (<0.05): рутинные новости, мелкие происшествия

   ВЛИЯНИЕ НА РЫНКИ (0-0.30):
   - Прямое немедленное (>0.25): санкции, дефолты, банкротства
   - Среднесрочное влияние (0.15-0.25): изменение процентных ставок, прогнозы
   - Косвенное влияние (0.05-0.15): новости о регулировании, отраслевые тренды
   - Минимальное влияние (<0.05): общие новости без финансового контекста

   УНИКАЛЬНОСТЬ (0-0.20):
   - Беспрецедентное событие (>0.15): первое в истории, революционное
   - Редкое событие (0.10-0.15): случается раз в несколько лет
   - Периодическое (0.05-0.10): бывает несколько раз в год
   - Обычное (<0.05): ежедневные рутинные новости

   СРОЧНОСТЬ (0-0.20):
   - Требует немедленной реакции (>0.15): breaking news, экстренные ситуации
   - Важно в ближайшие часы (0.10-0.15): свежие важные новости
   - Актуально в течение дня (0.05-0.10): текущие события
   - Не срочно (<0.05): плановые анонсы, отложенные события

   ВАЖНО:
   - Используй всю шкалу 0.00–1.00; не прилипать к 0.5/0.75.
   - 1.00 = экстраординарное мировое событие с немедленным рыночным воздействием.
   - 0.00 = отсутствие значимости для рынков.
   - Для нерелевантных новостей: hotness ≤ 0.10 и tickers = [].

3) Найди ВСЕ финансовые инструменты:
   - Тикеры акций (AAPL, TSLA, SBER, GAZP и т.д.)
   - Криптовалюты (BTC, ETH и т.д.)
   - Индексы (S&P500, MOEX, NASDAQ и т.д.)
   - Страны как рынки (USA, RU, CN, EU и т.д.)
   
Если финансовых инструментов нет - оставь массив пустым.

Формат вывода: строго ТОЛЬКО JSON, без текста до/после. Если новость нерелевантна, верни hotness в 0.00–0.10 и пустые tickers.

Формат ответа:
{{
    "hotness": 0.67,
    "tickers": ["SBER", "RU"]
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
            "temperature": 0.3,
            "max_tokens": 500
        }
        
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
            content = result['choices'][0]['message']['content']
            
            # Парсим JSON из ответа
            # Иногда модель добавляет markdown форматирование или дополнительный текст
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # Извлекаем только JSON часть (от { до })
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            analysis = json.loads(content.strip())
            
            # Валидация
            hotness = float(analysis.get('hotness', 0.5))
            hotness = max(0.0, min(1.0, hotness))  # Ограничиваем 0-1
            
            tickers = analysis.get('tickers', [])
            if not isinstance(tickers, list):
                tickers = []
            
            return {
                'hotness': hotness,
                'tickers': tickers
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка API запроса: {e}")
            return {'hotness': 0.5, 'tickers': []}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Ошибка парсинга ответа: {e}")
            print(f"Ответ: {content if 'content' in locals() else 'N/A'}")
            return {'hotness': 0.5, 'tickers': []}
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return {'hotness': 0.5, 'tickers': []}

