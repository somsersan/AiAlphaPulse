# 🎯 Использование разных моделей с ProxyAPI

## Быстрый старт

Установите переменную `LLM_MODEL` в `.env` файле:

```bash
# OpenAI модели
LLM_MODEL=gpt-4o-mini        # Самый дешёвый GPT
LLM_MODEL=gpt-4o             # Очень мощный
LLM_MODEL=gpt-4-turbo        # Быстрый GPT-4

# Anthropic Claude
LLM_MODEL=claude-3-5-haiku   # Быстрый и дешёвый
LLM_MODEL=claude-3-5-sonnet  # Мощный
LLM_MODEL=claude-3-opus      # Самый мощный (дорогой)

# OpenRouter модели (дешёвые альтернативы)
LLM_MODEL=deepseek/deepseek-chat          # Очень дешёвый
LLM_MODEL=meta-llama/llama-3.1-70b-instruct  # Llama 3.1
LLM_MODEL=mistralai/mistral-large         # Mistral Large
```

## Запуск с другой моделью

### 1. Через переменную окружения
```bash
export LLM_MODEL=gpt-4o-mini
python -m src.llm.runner --limit 10
```

### 2. Через параметр командной строки
```bash
python -m src.llm.runner --limit 10 --model claude-3-5-haiku
```

### 3. В docker-compose.yml
```yaml
environment:
  PROXYAPI_KEY: ${PROXYAPI_KEY}
  LLM_MODEL: claude-3-5-haiku  # Или любая другая модель
```

## Тестирование моделей

```bash
# Тест GPT-4o-mini
python -c "
from src.llm.proxyapi_client import ProxyAPIClient
client = ProxyAPIClient(model='gpt-4o-mini')
print(f'Модель: {client.model}')
print(f'Эндпоинт: {client.base_url}')
result = client.analyze_news('Test', 'Test content')
print(f'Hotness: {result[\"hotness\"]}')
"

# Тест Claude
python -c "
from src.llm.proxyapi_client import ProxyAPIClient
client = ProxyAPIClient(model='claude-3-5-haiku')
print(f'Модель: {client.model}')
print(f'Эндпоинт: {client.base_url}')
result = client.analyze_news('Test', 'Test content')
print(f'Hotness: {result[\"hotness\"]}')
"
```

## Выбор модели

| Модель | Стоимость | Скорость | Качество |
|--------|-----------|----------|----------|
| `deepseek/deepseek-chat` | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| `gpt-4o-mini` | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| `claude-3-5-haiku` | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| `meta-llama/llama-3.1-70b-instruct` | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| `gpt-4o` | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| `claude-3-5-sonnet` | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |

## Рекомендации

- **Для тестирования и разработки**: `deepseek/deepseek-chat` или `gpt-4o-mini`
- **Для production**: `claude-3-5-haiku` или `gpt-4o-mini`
- **Для максимального качества**: `claude-3-5-sonnet` или `gpt-4o`
