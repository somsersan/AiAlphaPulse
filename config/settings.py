"""
Настройки приложения.
"""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class DatabaseSettings(BaseSettings):
    """Настройки базы данных."""
    url: str = Field(default="postgresql://rss_user:rss_password@localhost:5432/rss_db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    class Config:
        env_prefix = "DATABASE_"


class APISettings(BaseSettings):
    """Настройки API."""
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    title: str = Field(default="RSS & Telegram Parser API", env="API_TITLE")
    description: str = Field(default="API для парсинга RSS-лент и Telegram каналов", env="API_DESCRIPTION")
    version: str = Field(default="1.0.0", env="API_VERSION")
    debug: bool = Field(default=False, env="API_DEBUG")

    class Config:
        env_prefix = "API_"


class ParsingSettings(BaseSettings):
    """Настройки парсинга."""
    auto_parse_interval: int = Field(default=60, env="PARSING_INTERVAL")  # секунды
    max_retries: int = Field(default=3, env="PARSING_MAX_RETRIES")
    timeout: int = Field(default=30, env="PARSING_TIMEOUT")
    words_per_minute: int = Field(default=200, env="PARSING_WORDS_PER_MINUTE")

    class Config:
        env_prefix = "PARSING_"


class RSSSettings(BaseSettings):
    """Настройки RSS."""
    urls: List[str] = Field(default_factory=lambda: [
    # 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    
    'https://cointelegraph.com/rss',
    
    'https://crypto.news/feed/',
    
    'https://bitcoinmagazine.com/.rss/full/',
    
    'https://www.theblock.co/rss.xml',
    
    'https://decrypt.co/feed',
    
    'https://cryptoslate.com/feed/',
    
    'https://news.bitcoin.com/feed/',
    
    'https://beincrypto.com/feed/',
    
    'https://u.today/rss'], env="RSS_URLS")

    class Config:
        env_prefix = "RSS_"


class TelegramSettings(BaseSettings):
    """Настройки Telegram."""
    channels: List[str] = Field(default_factory=lambda: [
        'RBCNews', 'vedomosti', 'kommersant', 'tass_agency', 'interfaxonline',
        'bitkogan', 'rbc_quote', 'banksta', 'cbonds', 'investfuture',
        'bezposhady', 'bloomeconomy', 'bloombusiness', 'economistg', 'BizLike',
        'finance_pro_tg', 'banki_economy', 'prbezposhady',
        'ru_holder', 'centralbank_russia', 'AlfaBank', 'multievan', 'bankvtb',
        'ozon_bank_official', 'auantonov', 'prostoecon', 'sberbank', 'cb_economics',
        'MarketOverview', 'frank_media', 'lemonfortea', 'div_invest', 'moneyhack',
        'finside', 'platformaonline', 'sf_education', 'intrinsic_value', 'finamalert',
        'SmartLab', 'tradernet', 'finam_trade', 'rutrade',
        'Bloomberg', 'Investingcom', 'TheEconomist', 'moneycontrolcom',
        'MarketAlert', 'Stocktwits', 'FinvizAlerts', 'CryptoMarkets', 'cbrstocks',
        'beststocks_usadividends', 'if_stocks', 'realvisiontv',
        'spydell_finance', 'WallStreetBets', 'SatoshiCalls', 'Hypercharts',
        'BiggerPockets', 'RyanScribner', 'JeffRose', 'MarkoWhiteBoardFinance',
        'DevinCarroll', 'BenHedges'
    ], env="TELEGRAM_CHANNELS")

    class Config:
        env_prefix = "TELEGRAM_"

class CryptoSettings(BaseSettings):
    """Настройки криптовалютных API."""
    
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    
    coinmarketcap_api_key: str = Field("", env="COINMARKETCAP_API_KEY")
    coinmarketcap_api_url: str = "https://pro-api.coinmarketcap.com/v1"
    
    binance_api_url: str = "https://api.binance.com/api/v3"
    
    top_cryptocurrencies: List[str] = Field(default_factory=lambda: [
        'bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano',
        'solana', 'polkadot', 'dogecoin', 'matic-network', 'litecoin',
        'chainlink', 'stellar', 'avalanche-2', 'cosmos', 'monero',
        'ethereum-classic', 'bitcoin-cash', 'filecoin', 'tron', 'eos'
    ])
    
    update_interval: int = 5


class Settings(BaseSettings):
    """Основные настройки приложения."""
    database: DatabaseSettings = DatabaseSettings()
    api: APISettings = APISettings()
    parsing: ParsingSettings = ParsingSettings()
    rss: RSSSettings = RSSSettings()
    telegram: TelegramSettings = TelegramSettings()
    crypto: CryptoSettings = CryptoSettings()

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

