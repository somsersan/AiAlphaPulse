"""
Доменные исключения.
Содержит специфичные для бизнес-логики исключения.
"""


class DomainException(Exception):
    """Базовое исключение для доменного слоя."""
    pass


class ArticleNotFoundError(DomainException):
    """Исключение, когда статья не найдена."""
    pass


class InvalidArticleError(DomainException):
    """Исключение, когда статья имеет невалидные данные."""
    pass


class ParsingError(DomainException):
    """Исключение при ошибке парсинга."""
    pass


class RSSFeedError(ParsingError):
    """Исключение при ошибке парсинга RSS ленты."""
    pass


class TelegramChannelError(ParsingError):
    """Исключение при ошибке парсинга Telegram канала."""
    pass


class DatabaseError(DomainException):
    """Исключение при ошибке работы с базой данных."""
    pass


class ConfigurationError(DomainException):
    """Исключение при ошибке конфигурации."""
    pass
