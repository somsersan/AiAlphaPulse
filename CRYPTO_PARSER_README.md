# 🤖 APIParser - Парсер криптовалютных данных

## Описание

`APIParser` - это компонент для парсинга данных о криптовалютах из различных API и преобразования их в статьи для сохранения в базе данных.

## Возможности

- 📊 **CoinGecko API** - получение данных о топ криптовалютах
- 📊 **CoinMarketCap API** - профессиональные данные о рынке (требует API ключ)
- 📊 **Binance API** - данные о торговых парах
- 🔄 **Автоматическое преобразование** в статьи ArticleModel
- 📈 **Анализ и статистика** для каждой криптовалюты

## Настройки

Парсер использует настройки из `CryptoSettings`:

```python
class CryptoSettings(BaseSettings):
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    coinmarketcap_api_key: str = Field("", env="COINMARKETCAP_API_KEY")
    coinmarketcap_api_url: str = "https://pro-api.coinmarketcap.com/v1"
    binance_api_url: str = "https://api.binance.com/api/v3"
    top_cryptocurrencies: List[str] = [
        'bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano',
        'solana', 'polkadot', 'dogecoin', 'matic-network', 'litecoin',
        'chainlink', 'stellar', 'avalanche-2', 'cosmos', 'monero',
        'ethereum-classic', 'bitcoin-cash', 'filecoin', 'tron', 'eos'
    ]
    update_interval: int = 5
```

## Использование

### 1. Прямое использование APIParser

```python
import asyncio
from config.settings import settings
from infrastructure.parsers.api_parser import APIParser

async def parse_crypto_data():
    # Создаем парсер
    api_parser = APIParser(settings.crypto)
    
    # Используем async context manager
    async with api_parser:
        articles = await api_parser.parse_crypto_data()
        
        for article in articles:
            print(f"📰 {article.title}")
            print(f"   Источник: {article.source}")
            print(f"   Категория: {article.category}")
            print(f"   Слов: {article.word_count}")
            print()

# Запуск
asyncio.run(parse_crypto_data())
```

### 2. Использование через ParsingService

```python
from core.services.parsing_service import ParsingService
from infrastructure.parsers.api_parser import APIParser

# Создаем сервис с API парсером
parsing_service = ParsingService(
    article_repository=article_repo,
    feed_repository=feed_repo,
    rss_parser=rss_parser,
    telegram_parser=telegram_parser,
    api_parser=APIParser(settings.crypto)  # Добавляем API парсер
)

# Парсим все источники (включая криптовалюты)
results = await parsing_service.parse_all_sources()
print(f"Получено статей: {results['total']}")
print(f"Из API: {results.get('api', 0)}")
```

## Структура данных

### Входные данные (API)

**CoinGecko:**
```json
{
  "id": "bitcoin",
  "name": "Bitcoin",
  "symbol": "btc",
  "current_price": 45000.0,
  "market_cap": 850000000000,
  "price_change_percentage_24h": 2.5,
  "total_volume": 25000000000,
  "high_24h": 46000.0,
  "low_24h": 44000.0,
  "image": "https://example.com/bitcoin.png"
}
```

**CoinMarketCap:**
```json
{
  "name": "Bitcoin",
  "symbol": "BTC",
  "quote": {
    "USD": {
      "price": 45000.0,
      "market_cap": 850000000000,
      "percent_change_24h": 2.5,
      "volume_24h": 25000000000
    }
  },
  "slug": "bitcoin"
}
```

**Binance:**
```json
{
  "symbol": "BTCUSDT",
  "lastPrice": "45000.00",
  "priceChangePercent": "2.50",
  "volume": "25000000000"
}
```

### Выходные данные (Article)

```python
Article(
    id=None,
    title="Bitcoin (BTC): $45,000.00 (+2.50%)",
    link="https://www.coingecko.com/en/coins/bitcoin",
    published=datetime.now(timezone.utc),
    summary="Bitcoin торгуется на уровне $45,000.00 с изменением +2.50% за 24 часа...",
    source="CoinGecko API",
    feed_url="https://api.coingecko.com/api/v3",
    content="<h2>Анализ Bitcoin (BTC)</h2><p><strong>Текущая цена:</strong> $45,000.00</p>...",
    author="AiAlphaPulse Crypto Parser",
    category="Cryptocurrency",
    image_url="https://example.com/bitcoin.png",
    word_count=150,
    reading_time=1,
    is_processed=False,
    created_at=datetime.now(timezone.utc)
)
```

## Особенности

### 1. Асинхронная работа
- Использует `aiohttp` для асинхронных HTTP запросов
- Поддерживает async context manager
- Параллельная обработка нескольких API

### 2. Обработка ошибок
- Graceful handling API ошибок
- Логирование проблемных запросов
- Продолжение работы при сбоях отдельных API

### 3. Контент-анализ
- Автоматический подсчет слов
- Расчет времени чтения (200 слов/мин)
- Генерация аналитических текстов

### 4. Источники данных
- **CoinGecko**: Бесплатный, без API ключа
- **CoinMarketCap**: Профессиональный, требует API ключ
- **Binance**: Торговые данные, без API ключа

## Тестирование

Запустите тесты для проверки работы:

```bash
# Тест настроек и создания парсера
python test_crypto_parser.py

# Полный пример с парсингом
python crypto_parser_example.py
```

## Требования

Добавьте в `requirements.txt`:
```
aiohttp==3.9.1
```

## Интеграция с существующей системой

1. **ParsingService** - автоматически включает API парсер
2. **ArticleRepository** - сохраняет статьи в базу данных
3. **ArticleModel** - соответствует структуре базы данных
4. **SourceType.API** - новый тип источника для криптовалют

## Примеры использования

### Получение данных о Bitcoin
```python
async with APIParser(settings.crypto) as parser:
    articles = await parser.parse_crypto_data()
    bitcoin_articles = [a for a in articles if 'bitcoin' in a.title.lower()]
```

### Мониторинг топ криптовалют
```python
# Парсим только топ-5 криптовалют
settings.crypto.top_cryptocurrencies = ['bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano']
```

### Настройка интервала обновления
```python
# Обновление каждые 10 минут
settings.crypto.update_interval = 10
```

## Логирование

Парсер выводит информацию о процессе:
- ✅ Успешные запросы к API
- ❌ Ошибки парсинга
- 📊 Статистика полученных статей
- 🔄 Статус обработки

## Производительность

- **CoinGecko**: ~20 криптовалют за 2-3 секунды
- **CoinMarketCap**: ~20 криптовалют за 1-2 секунды (с API ключом)
- **Binance**: ~5 торговых пар за 1 секунду
- **Общее время**: 5-10 секунд для всех источников

