#!/usr/bin/env python3
"""Тест подключения к OpenRouter API"""
import os
import sys
import requests
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

def test_api_key():
    """Проверка API ключа OpenRouter"""
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY не установлен")
        print("\nУстановите переменную окружения:")
        print("  export OPENROUTER_API_KEY='ваш-ключ'")
        return False
    
    print(f"✅ API ключ найден: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Длина: {len(api_key)} символов")
    
    # Проверяем доступность API
    print("\n🔍 Проверяем подключение к OpenRouter...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-username/AiAlphaPulse",
        "X-Title": "AiAlphaPulse News Analyzer"
    }
    
    # Простой тестовый запрос
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Say 'test successful' if you can read this"}
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📡 Статус код: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ API работает!")
            print(f"   Ответ: {content}")
            return True
            
        elif response.status_code == 403:
            error = response.json() if response.content else {}
            print(f"❌ Ошибка 403 Forbidden")
            print(f"\nВозможные причины:")
            print(f"1. API ключ неверный или истек")
            print(f"2. Недостаточно средств на балансе OpenRouter")
            print(f"3. API ключ не активирован")
            print(f"\nДетали ошибки: {error}")
            print(f"\n📝 Что делать:")
            print(f"   1. Проверьте баланс: https://openrouter.ai/credits")
            print(f"   2. Проверьте API ключ: https://openrouter.ai/keys")
            print(f"   3. Пополните баланс если нужно")
            return False
            
        elif response.status_code == 429:
            print(f"⚠️ Превышен лимит запросов (429)")
            print(f"   Подождите немного и попробуйте снова")
            return False
            
        else:
            print(f"❌ Неожиданный статус: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("🧪 ТЕСТ ПОДКЛЮЧЕНИЯ К OPENROUTER API")
    print("="*60)
    print()
    
    success = test_api_key()
    
    print()
    print("="*60)
    if success:
        print("✅ Тест пройден! Можно запускать обработку кластеров")
        print()
        print("Запустите:")
        print("  python3 -m src.llm.runner --limit 2")
        sys.exit(0)
    else:
        print("❌ Тест не пройден. Исправьте проблемы выше")
        sys.exit(1)

