"""
Парсер для API криптовалютных данных.
Получает данные из различных криптовалютных API и преобразует их в статьи.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config.settings import CryptoSettings
from core.domain.entities import Article, SourceType
from core.domain.exceptions import ParsingError


@dataclass
class CryptoData:
    """Структура данных о криптовалюте."""
    id: str
    name: str
    symbol: str
    current_price: float
    market_cap: float
    price_change_24h: float
    price_change_percentage_24h: float
    volume_24h: float
    last_updated: datetime


class APIParser:
    """Парсер для криптовалютных API."""
    
    def __init__(self, crypto_settings: CryptoSettings):
        self.crypto_settings = crypto_settings
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'AiAlphaPulse/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        if self.session:
            await self.session.close()
    
    async def parse_crypto_data(self) -> List[Article]:
        """
        Парсит данные о криптовалютах из различных API.
        Возвращает список статей для сохранения в базу данных.
        """
        if not self.session:
            raise ParsingError("Session not initialized. Use async context manager.")
        
        articles = []
        
        try:
            print("🔄 Парсинг CoinGecko API...")
            # Получаем данные из CoinGecko
            coingecko_articles = await self._parse_coingecko_data()
            articles.extend(coingecko_articles)
            print(f"✅ CoinGecko: получено {len(coingecko_articles)} статей")
            
            # Получаем данные из CoinMarketCap (если есть API ключ)
            if self.crypto_settings.coinmarketcap_api_key:
                print("🔄 Парсинг CoinMarketCap API...")
                coinmarketcap_articles = await self._parse_coinmarketcap_data()
                articles.extend(coinmarketcap_articles)
                print(f"✅ CoinMarketCap: получено {len(coinmarketcap_articles)} статей")
            else:
                print("⚠️ CoinMarketCap API ключ не настроен")
            
            print("🔄 Парсинг Binance API...")
            # Получаем данные из Binance
            binance_articles = await self._parse_binance_data()
            articles.extend(binance_articles)
            print(f"✅ Binance: получено {len(binance_articles)} статей")
            
        except Exception as e:
            print(f"❌ Ошибка парсинга криптовалютных данных: {str(e)}")
            import traceback
            traceback.print_exc()
            # Не прерываем выполнение, возвращаем то что получили
        
        return articles
    
    async def _parse_coingecko_data(self) -> List[Article]:
        """Парсит данные из CoinGecko API."""
        articles = []
        
        try:
            # Получаем данные о топ криптовалютах
            url = f"{self.crypto_settings.coingecko_api_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': ','.join(self.crypto_settings.top_cryptocurrencies),
                'order': 'market_cap_desc',
                'per_page': 20,
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '24h'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for coin_data in data:
                        article = self._create_crypto_article_from_coingecko(coin_data)
                        articles.append(article)
                else:
                    print(f"CoinGecko API error: {response.status}")
                    
        except Exception as e:
            print(f"Error parsing CoinGecko data: {e}")
        
        return articles
    
    async def _parse_coinmarketcap_data(self) -> List[Article]:
        """Парсит данные из CoinMarketCap API."""
        articles = []
        
        try:
            url = f"{self.crypto_settings.coinmarketcap_api_url}/cryptocurrency/listings/latest"
            headers = {
                'X-CMC_PRO_API_KEY': self.crypto_settings.coinmarketcap_api_key,
                'Accept': 'application/json'
            }
            params = {
                'start': 1,
                'limit': 20,
                'convert': 'USD'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for coin_data in data.get('data', []):
                        article = self._create_crypto_article_from_coinmarketcap(coin_data)
                        articles.append(article)
                else:
                    print(f"CoinMarketCap API error: {response.status}")
                    
        except Exception as e:
            print(f"Error parsing CoinMarketCap data: {e}")
        
        return articles
    
    async def _parse_binance_data(self) -> List[Article]:
        """Парсит данные из Binance API."""
        articles = []
        
        try:
            # Получаем 24hr ticker statistics
            url = f"{self.crypto_settings.binance_api_url}/ticker/24hr"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Фильтруем только популярные пары
                    popular_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT']
                    
                    for ticker_data in data:
                        if ticker_data['symbol'] in popular_pairs:
                            article = self._create_crypto_article_from_binance(ticker_data)
                            articles.append(article)
                else:
                    print(f"Binance API error: {response.status}")
                    
        except Exception as e:
            print(f"Error parsing Binance data: {e}")
        
        return articles
    
    def _create_crypto_article_from_coingecko(self, coin_data: Dict[str, Any]) -> Article:
        """Создает статью из данных CoinGecko."""
        current_time = datetime.now(timezone.utc)
        
        # Формируем заголовок
        name = coin_data.get('name', 'Unknown')
        symbol = coin_data.get('symbol', '').upper()
        price = coin_data.get('current_price', 0)
        change_24h = coin_data.get('price_change_percentage_24h', 0)
        
        title = f"{name} ({symbol}): ${price:,.2f} ({change_24h:+.2f}%)"
        
        # Формируем контент
        market_cap = coin_data.get('market_cap', 0)
        volume_24h = coin_data.get('total_volume', 0)
        high_24h = coin_data.get('high_24h', 0)
        low_24h = coin_data.get('low_24h', 0)
        
        content = f"""
        <h2>Анализ {name} ({symbol})</h2>
        <p><strong>Текущая цена:</strong> ${price:,.2f}</p>
        <p><strong>Изменение за 24ч:</strong> {change_24h:+.2f}%</p>
        <p><strong>Рыночная капитализация:</strong> ${market_cap:,.0f}</p>
        <p><strong>Объем торгов за 24ч:</strong> ${volume_24h:,.0f}</p>
        <p><strong>Максимум за 24ч:</strong> ${high_24h:,.2f}</p>
        <p><strong>Минимум за 24ч:</strong> ${low_24h:,.2f}</p>
        
        <h3>Технический анализ</h3>
        <p>Криптовалюта {name} показывает {'положительную' if change_24h > 0 else 'отрицательную'} динамику за последние 24 часа. 
        {'Рост' if change_24h > 0 else 'Падение'} составляет {abs(change_24h):.2f}%.</p>
        
        <h3>Рыночные показатели</h3>
        <p>Рыночная капитализация составляет ${market_cap:,.0f}, что делает {name} {'крупной' if market_cap > 10000000000 else 'средней' if market_cap > 1000000000 else 'малой'} криптовалютой по рыночной капитализации.</p>
        """
        
        # Формируем краткое описание
        summary = f"{name} торгуется на уровне ${price:,.2f} с изменением {change_24h:+.2f}% за 24 часа. Рыночная капитализация: ${market_cap:,.0f}."
        
        # Подсчитываем статистику
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        print(word_count, reading_time)
        
        return Article(
            id=None,
            title=title,
            link=f"https://www.coingecko.com/en/coins/{coin_data.get('id', 'unknown')}",
            published=current_time,
            summary=summary,
            source="CoinGecko API",
            feed_url="https://api.coingecko.com/api/v3",
            content=content.strip(),
            author="AiAlphaPulse Crypto Parser",
            category="Cryptocurrency",
            image_url=coin_data.get('image', ''),
            word_count=word_count,
            reading_time=reading_time,
            is_processed=False,
            created_at=current_time
        )
    
    def _create_crypto_article_from_coinmarketcap(self, coin_data: Dict[str, Any]) -> Article:
        """Создает статью из данных CoinMarketCap."""
        current_time = datetime.now(timezone.utc)
        
        name = coin_data.get('name', 'Unknown')
        symbol = coin_data.get('symbol', '').upper()
        quote = coin_data.get('quote', {}).get('USD', {})
        price = quote.get('price', 0)
        change_24h = quote.get('percent_change_24h', 0)
        
        title = f"{name} ({symbol}): ${price:,.2f} ({change_24h:+.2f}%)"
        
        market_cap = quote.get('market_cap', 0)
        volume_24h = quote.get('volume_24h', 0)
        
        content = f"""
        <h2>Анализ {name} ({symbol})</h2>
        <p><strong>Текущая цена:</strong> ${price:,.2f}</p>
        <p><strong>Изменение за 24ч:</strong> {change_24h:+.2f}%</p>
        <p><strong>Рыночная капитализация:</strong> ${market_cap:,.0f}</p>
        <p><strong>Объем торгов за 24ч:</strong> ${volume_24h:,.0f}</p>
        
        <h3>Рыночный анализ</h3>
        <p>Криптовалюта {name} демонстрирует {'рост' if change_24h > 0 else 'падение'} на {abs(change_24h):.2f}% за последние 24 часа.</p>
        """
        
        summary = f"{name} торгуется на уровне ${price:,.2f} с изменением {change_24h:+.2f}% за 24 часа."
        
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        
        return Article(
            id=None,
            title=title,
            link=f"https://coinmarketcap.com/currencies/{coin_data.get('slug', 'unknown')}/",
            published=current_time,
            summary=summary,
            source="CoinMarketCap API",
            feed_url="https://pro-api.coinmarketcap.com/v1",
            content=content.strip(),
            author="AiAlphaPulse Crypto Parser",
            category="Cryptocurrency",
            image_url="",
            word_count=word_count,
            reading_time=reading_time,
            is_processed=False,
            created_at=current_time
        )
    
    def _create_crypto_article_from_binance(self, ticker_data: Dict[str, Any]) -> Article:
        """Создает статью из данных Binance."""
        current_time = datetime.now(timezone.utc)
        
        symbol = ticker_data.get('symbol', '')
        price = float(ticker_data.get('lastPrice', 0))
        change_24h = float(ticker_data.get('priceChangePercent', 0))
        volume = float(ticker_data.get('volume', 0))
        
        # Преобразуем символ пары в читаемый формат
        if symbol.endswith('USDT'):
            crypto_name = symbol[:-4]
        else:
            crypto_name = symbol
        
        title = f"{crypto_name}: ${price:,.2f} ({change_24h:+.2f}%)"
        
        content = f"""
        <h2>Анализ {crypto_name}</h2>
        <p><strong>Текущая цена:</strong> ${price:,.2f}</p>
        <p><strong>Изменение за 24ч:</strong> {change_24h:+.2f}%</p>
        <p><strong>Объем торгов за 24ч:</strong> {volume:,.0f}</p>
        
        <h3>Торговая активность</h3>
        <p>Пара {crypto_name} показывает {'активный рост' if change_24h > 0 else 'снижение'} на {abs(change_24h):.2f}% за последние 24 часа.</p>
        """
        
        summary = f"{crypto_name} торгуется на уровне ${price:,.2f} с изменением {change_24h:+.2f}% за 24 часа."
        
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        
        return Article(
            id=None,
            title=title,
            link=f"https://www.binance.com/en/trade/{crypto_name}_USDT",
            published=current_time,
            summary=summary,
            source="Binance API",
            feed_url="https://api.binance.com/api/v3",
            content=content.strip(),
            author="AiAlphaPulse Crypto Parser",
            category="Cryptocurrency",
            image_url="",
            word_count=word_count,
            reading_time=reading_time,
            is_processed=False,
            created_at=current_time
        )