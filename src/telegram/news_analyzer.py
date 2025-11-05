"""News analyzer for generating detailed information via LLM"""
import json
import os
from typing import Dict
from ..llm.proxyapi_client import ProxyAPIClient


class NewsAnalyzer:
    """Generates detailed analytics for news"""
    
    def __init__(self, api_key: str = None, model: str = None):
        # Use more powerful model for detailed analysis
        # LLM_ANALYSIS_MODEL - for detailed analysis (default Claude 3.5 Sonnet)
        # LLM_MODEL - for quick hotness evaluation
        self.analysis_model = model or os.getenv("LLM_ANALYSIS_MODEL", "anthropic/claude-3.5-sonnet")
        self.llm_client = ProxyAPIClient(api_key=api_key, model=self.analysis_model)
    
    def generate_full_analysis(self, news: Dict) -> Dict:
        """
        Generates full news analysis in analytical card format
        
        Args:
            news: dict with headline, content, tickers, hotness, urls, published_at, source
            
        Returns:
            {
                'analysis_text': str - ready card in Markdown format
            }
        """
        
        print("\n" + "="*60)
        print("🔍 НАЧАЛО ГЕНЕРАЦИИ ДЕТАЛЬНОГО АНАЛИЗА")
        print("="*60)
        
        headline = news.get('headline', '')
        content = news.get('content', '')
        tickers = news.get('tickers', [])
        hotness = news.get('hotness', 0)
        urls = news.get('urls', [])
        published_at = news.get('published_at', '')
        source = news.get('source', 'Unknown source')
        
        print(f"📰 Новость: {headline[:50]}...")
        print(f"🔢 Hotness: {hotness}")
        print(f"📎 URL: {urls[0] if urls else 'нет'}")
        
        # Create prompt for analytical card generation
        prompt = self._create_analysis_card_prompt(headline, content, tickers, hotness, urls, published_at, source)
        
        headers = {
            "Authorization": f"Bearer {self.llm_client.api_key}",
            "Content-Type": "application/json"
        }
        
        # Формируем payload в зависимости от формата API
        api_format = self.llm_client.api_format
        print(f"🔧 Формат API: {api_format}")
        print(f"🌐 Base URL: {self.llm_client.base_url}")
        print(f"🤖 Исходная модель: {self.analysis_model}")
        print(f"🎯 Используемая модель: {self.llm_client.model}")
        
        if api_format == "anthropic":
            payload = {
                "model": self.llm_client.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
                "temperature": 0.3
            }
        else:
            payload = {
                "model": self.llm_client.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1500
            }
        
        print(f"📦 Payload keys: {list(payload.keys())}")
        print(f"📝 Prompt length: {len(prompt)} символов")
        
        # Детальное логирование для отладки
        print(f"\n🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ЗАПРОСЕ:")
        print(f"   📍 URL: {self.llm_client.base_url}")
        print(f"   🔑 API Key (первые 10 символов): {headers.get('Authorization', 'N/A')[:20]}...")
        print(f"   🤖 Модель в payload: {payload.get('model', 'N/A')}")
        print(f"   📊 Формат API: {api_format}")
        print(f"   📝 Max tokens: {payload.get('max_tokens', 'N/A')}")
        print(f"   🌡️ Temperature: {payload.get('temperature', 'N/A')}")
        print(f"   💬 Количество сообщений: {len(payload.get('messages', []))}")
        
        try:
            import requests
            print(f"\n🚀 Отправка запроса к API...")
            print(f"   Согласно документации ProxyAPI:")
            print(f"   - URL должен быть: https://api.proxyapi.ru/anthropic/v1/messages")
            print(f"   - Модель должна быть в формате с дефисами: claude-3-5-sonnet")
            print(f"   - Authorization: Bearer <КЛЮЧ>")
            
            try:
                response = requests.post(
                    self.llm_client.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
            except requests.exceptions.Timeout:
                print(f"\n❌ ОШИБКА: Превышено время ожидания ответа от API (30 секунд)")
                print(f"   URL: {self.llm_client.base_url}")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )
            except requests.exceptions.ConnectionError as e:
                print(f"\n❌ ОШИБКА: Ошибка подключения к API")
                print(f"   Детали: {e}")
                print(f"   URL: {self.llm_client.base_url}")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )
            except requests.exceptions.RequestException as e:
                print(f"\n❌ ОШИБКА: Ошибка при запросе к API")
                print(f"   Тип ошибки: {type(e).__name__}")
                print(f"   Детали: {e}")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )
            
            print(f"\n📡 ОТВЕТ ОТ API:")
            print(f"   HTTP Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_details = response.text if hasattr(response, 'text') else str(response.status_code)
                try:
                    error_json = response.json()
                    print(f"   📋 JSON ошибки: {error_json}")
                except:
                    print(f"   📋 Текст ошибки: {error_details}")
                
                print(f"\n❌ ОШИБКА HTTP {response.status_code}")
                print(f"   Детали ошибки: {error_details}")
                print(f"   URL: {self.llm_client.base_url}")
                print(f"   Модель в payload: {payload.get('model', 'N/A')}")
                print(f"   Формат API: {api_format}")
                print(f"\n💡 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
                print(f"   1. Неправильное имя модели (должно быть с дефисами: claude-3-5-sonnet)")
                print(f"   2. Модель не поддерживается ProxyAPI")
                print(f"   3. Неверный API ключ или недостаточно средств")
                print(f"   4. Неправильный формат запроса")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )
            
            print(f"✅ Успешный ответ от API")
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"❌ ОШИБКА: Не удалось распарсить JSON ответ от API")
                print(f"   Ошибка: {e}")
                print(f"   Текст ответа (первые 500 символов): {response.text[:500] if hasattr(response, 'text') else 'N/A'}")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )
            
            print(f"📋 Ключи в ответе: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            
            # Извлекаем контент в зависимости от формата API
            if api_format == "anthropic":
                # Anthropic: result['content'][0]['text']
                print(f"🔍 Поиск контента в формате Anthropic...")
                if 'content' not in result:
                    print(f"❌ ОШИБКА: Anthropic API response missing 'content' field")
                    print(f"   Доступные ключи: {list(result.keys())}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                # Проверяем, что content - это список и не пустой
                if not isinstance(result['content'], list) or len(result['content']) == 0:
                    print(f"❌ ОШИБКА: Anthropic API response 'content' is not a list or is empty")
                    print(f"   Тип content: {type(result['content'])}")
                    print(f"   Значение content: {result['content']}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                # Проверяем, что первый элемент - это словарь
                first_content = result['content'][0]
                if not isinstance(first_content, dict):
                    print(f"❌ ОШИБКА: Anthropic API response 'content[0]' is not a dict")
                    print(f"   Тип content[0]: {type(first_content)}")
                    print(f"   Значение content[0]: {first_content}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                # Извлекаем текст
                content = first_content.get('text', '')
                if not content:
                    # Возможно, текст находится в другом поле
                    print(f"⚠️ Поле 'text' пустое, ищем альтернативные поля...")
                    print(f"   Ключи в content[0]: {list(first_content.keys())}")
                    # Пробуем найти текст в других возможных полях
                    for key in ['content', 'message', 'text']:
                        if key in first_content:
                            potential_text = first_content[key]
                            if isinstance(potential_text, str) and potential_text.strip():
                                content = potential_text
                                print(f"   ✅ Найден текст в поле '{key}'")
                                break
                
                if not content:
                    print(f"❌ ОШИБКА: Не удалось извлечь текст из ответа Anthropic API")
                    print(f"   Структура content[0]: {first_content}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                print(f"✅ Контент извлечен из result['content'][0]['text']")
                print(f"   Длина контента: {len(content)} символов")
            else:
                # OpenAI и OpenRouter: result['choices'][0]['message']['content']
                print(f"🔍 Поиск контента в формате OpenAI/OpenRouter...")
                if 'choices' not in result:
                    print(f"❌ ОШИБКА: API response missing 'choices' field")
                    print(f"   Доступные ключи: {list(result.keys())}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                # Проверяем, что choices - это список и не пустой
                if not isinstance(result['choices'], list) or len(result['choices']) == 0:
                    print(f"❌ ОШИБКА: API response 'choices' is not a list or is empty")
                    print(f"   Тип choices: {type(result['choices'])}")
                    print(f"   Значение choices: {result['choices']}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                # Проверяем структуру первого choice
                first_choice = result['choices'][0]
                if not isinstance(first_choice, dict):
                    print(f"❌ ОШИБКА: API response 'choices[0]' is not a dict")
                    print(f"   Тип choices[0]: {type(first_choice)}")
                    print(f"   Значение choices[0]: {first_choice}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                # Извлекаем message
                message = first_choice.get('message', {})
                if not isinstance(message, dict):
                    print(f"❌ ОШИБКА: API response 'choices[0].message' is not a dict")
                    print(f"   Тип message: {type(message)}")
                    print(f"   Значение message: {message}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                content = message.get('content', '')
                if not content:
                    print(f"❌ ОШИБКА: Не удалось извлечь текст из ответа API")
                    print(f"   Структура choices[0]: {first_choice}")
                    print(f"   Полный ответ: {str(result)[:500]}")
                    return self._get_fallback_analysis(
                        news.get('hotness', 0),
                        news.get('urls', []),
                        news.get('published_at', ''),
                        news.get('source', 'Unknown source')
                    )
                
                print(f"✅ Контент извлечен из result['choices'][0]['message']['content']")
                print(f"   Длина контента: {len(content)} символов")
            
            # Проверяем, что контент не пустой
            if not content or not content.strip():
                print(f"❌ ОШИБКА: пустой ответ от LLM")
                print(f"   Структура ответа: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                print(f"   Первые 200 символов ответа: {str(result)[:200]}")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )

            # Normalize model response: remove markdown fences and extract JSON
            print(f"\n🔧 Обработка ответа LLM...")
            import re
            raw_content = content or ""
            print(f"   Исходный контент (первые 200 символов): {raw_content[:200]}")
            
            if "```json" in raw_content:
                print(f"   Найден блок ```json")
                try:
                    content = raw_content.split("```json", 1)[1].split("```", 1)[0]
                    print(f"   Извлечен JSON из блока")
                except Exception as e:
                    print(f"   ⚠️ Ошибка извлечения из ```json: {e}")
                    content = raw_content
            elif "```" in raw_content:
                print(f"   Найден блок ```")
                try:
                    content = raw_content.split("```", 1)[1].split("```", 1)[0]
                    print(f"   Извлечен контент из блока")
                except Exception as e:
                    print(f"   ⚠️ Ошибка извлечения из ```: {e}")
                    content = raw_content
            else:
                print(f"   Markdown блоки не найдены, используем весь контент")
                content = raw_content

            # Extract JSON substring by outer curly braces
            print(f"   Поиск JSON объекта...")
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
                print(f"   ✅ JSON объект найден")
            else:
                print(f"   ⚠️ JSON объект не найден регулярным выражением")

            # Remove problematic control characters, keeping line breaks
            def _sanitize(s: str) -> str:
                if not isinstance(s, str):
                    return s
                # Remove BOM and null bytes/vertical tabs/form feeds
                s = s.replace('\ufeff', '')
                s = s.replace('\x00', '').replace('\x0b', ' ').replace('\x0c', ' ')
                return s

            content = _sanitize(content)
            print(f"   Контент после очистки (первые 300 символов): {content[:300]}")

            # Check that valid content remains after all processing
            if not content or not content.strip():
                print(f"❌ ОШИБКА: пустой контент после обработки")
                return self._get_fallback_analysis(
                    news.get('hotness', 0),
                    news.get('urls', []),
                    news.get('published_at', ''),
                    news.get('source', 'Unknown source')
                )

            # Parse JSON, allowing unescaped control characters inside strings
            print(f"\n📊 Парсинг JSON...")
            try:
                analysis = json.loads(content.strip(), strict=False)
                print(f"✅ JSON успешно распарсен")
                print(f"   Ключи в анализе: {list(analysis.keys()) if isinstance(analysis, dict) else 'not a dict'}")
                print(f"   Наличие analysis_text: {'analysis_text' in analysis if isinstance(analysis, dict) else False}")
                print("="*60)
                print("✅ ГЕНЕРАЦИЯ АНАЛИЗА ЗАВЕРШЕНА УСПЕШНО")
                print("="*60 + "\n")
                return analysis
            except json.JSONDecodeError as e:
                print(f"❌ ОШИБКА парсинга JSON: {e}")
                print(f"   Контент для парсинга (первые 500 символов): {content[:500]}")
                raise
            
        except json.JSONDecodeError as e:
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: невалидный JSON")
            print(f"   Ошибка: {e}")
            print(f"   Полученный контент (первые 500 символов): {content[:500] if 'content' in locals() else 'N/A'}")
            import traceback
            traceback.print_exc()
            print("="*60)
            print("❌ ГЕНЕРАЦИЯ АНАЛИЗА ЗАВЕРШЕНА С ОШИБКОЙ")
            print("="*60 + "\n")
            return self._get_fallback_analysis(
                news.get('hotness', 0),
                news.get('urls', []),
                news.get('published_at', ''),
                news.get('source', 'Unknown source')
            )
        except KeyError as e:
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: отсутствует ключ в ответе")
            print(f"   Отсутствующий ключ: {e}")
            print(f"   Структура ответа: {list(result.keys()) if 'result' in locals() and isinstance(result, dict) else 'N/A'}")
            import traceback
            traceback.print_exc()
            print("="*60)
            print("❌ ГЕНЕРАЦИЯ АНАЛИЗА ЗАВЕРШЕНА С ОШИБКОЙ")
            print("="*60 + "\n")
            return self._get_fallback_analysis(
                news.get('hotness', 0),
                news.get('urls', []),
                news.get('published_at', ''),
                news.get('source', 'Unknown source')
            )
        except Exception as e:
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: неожиданная ошибка")
            print(f"   Тип ошибки: {type(e).__name__}")
            print(f"   Сообщение: {e}")
            import traceback
            traceback.print_exc()
            print("="*60)
            print("❌ ГЕНЕРАЦИЯ АНАЛИЗА ЗАВЕРШЕНА С ОШИБКОЙ")
            print("="*60 + "\n")
            return self._get_fallback_analysis(
                news.get('hotness', 0),
                news.get('urls', []),
                news.get('published_at', ''),
                news.get('source', 'Unknown source')
            )
    
    def _create_analysis_card_prompt(self, headline: str, content: str, tickers: list, hotness: float, urls: list, published_at: str, source: str) -> str:
        """Prompt for generating news analytical card"""
        tickers_str = ', '.join(tickers) if tickers else '—'
        url_str = urls[0] if urls else 'no link'
        
        # Always use English for user-facing content
        lang_instruction = "in English"
        
        return f"""You are a financial news analytics agent for the AI ALPHA PULSE Telegram bot. Your task is to create a compact, explainable analytical card {lang_instruction}.

IMPORTANT: The news article may be in any language (Russian, English, etc.), but your analysis MUST be written entirely in English. Translate and analyze the content, then present your analysis in English.

INPUT DATA:
Headline: {headline}
Text: {content[:2000]}
Tickers: {tickers_str}
Source: {source}
Publication time: {published_at}
URL: {url_str}
Hotness score: {hotness:.2f}

OUTPUT REQUIREMENTS:
Create an analytical card in Markdown format (Telegram-compatible). Card language: {lang_instruction}. IMPORTANT: All text must be in English, regardless of the source news language.

MANDATORY FIELDS (strictly in this order):

1. TL;DR (20-30 words): News essence and its impact on markets/assets
2. Key facts (2-4 points): Specific facts from text, no speculation
3. Affected assets: Comma-separated ticker list or "—"
4. Sentiment score: Number from -1 to 1 and brief explanation (why positive/negative/neutral)
5. News score: Number from 0 to 1 and main drivers (sentiment / mentions / authority)
6. Recommendation: "Monitor" / "Bullish (consider buy)" / "Bearish (consider sell)" / "No action" + 1-2 sentence explanation
7. Confidence: "Low" / "Medium" / "High" + justification (why this confidence level)

STYLE:
- Brief, neutral, business-like. Maximum 700 characters
- Use phrases: "consider", "monitor", "may indicate" (don't give direct financial advice)
- If data is insufficient — indicate this in Confidence and TL;DR
- Don't make up statistics if they're not in the text
- Use emojis where appropriate

Reply ONLY in JSON format:
{{
    "analysis_text": "🔎 *TL;DR:* ...\\n\\n📌 *Key facts:*\\n• Fact 1\\n• Fact 2\\n• Fact 3\\n\\n📈 *Affected assets:* ...\\n💡 *Sentiment:* ... — ...\\n⭐ *News score:* ... — drivers: ...\\n\\n🧭 *Recommendation:* ... — ...\\n🔒 *Confidence:* ... — ...\\n\\n🔗 {url_str}"
}}

IMPORTANT: All card text must be in one line analysis_text with escaped line breaks (\\n). Use Markdown formatting (*bold text*) for field headers."""
    
    def _get_fallback_analysis(self, hotness: float, urls: list, published_at: str, source: str) -> Dict:
        """Fallback analysis on LLM error"""
        url_str = urls[0] if urls else 'no link'
        
        fallback_text = f"""🔎 *TL;DR:* Analysis temporarily unavailable — LLM processing error.

📌 *Key facts:*
• News requires manual analysis
• Automatic processing failed

📈 *Affected assets:* —
💡 *Sentiment:* 0.0 — not determined
⭐ *News score:* {hotness:.2f} — baseline hotness score

🧭 *Recommendation:* Monitor — additional analysis required
🔒 *Confidence:* Low — automatic analysis unavailable

🔗 {url_str}"""
        
        return {
            'analysis_text': fallback_text
        }

