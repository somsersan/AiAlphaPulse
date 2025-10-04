"""
Value Objects для доменной модели.
Value Objects - это объекты, которые определяются только своими атрибутами.
"""

from dataclasses import dataclass
from typing import List
import re


@dataclass(frozen=True)
class URL:
    """Value Object для URL."""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("URL cannot be empty")
        # Простая валидация URL
        if not (self.value.startswith('http://') or self.value.startswith('https://')):
            raise ValueError("URL must start with http:// or https://")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Email:
    """Value Object для email."""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Email cannot be empty")
        # Простая валидация email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, self.value):
            raise ValueError("Invalid email format")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Category:
    """Value Object для категории статьи."""
    name: str
    keywords: List[str]

    def __post_init__(self):
        if not self.name:
            raise ValueError("Category name cannot be empty")
        if not self.keywords:
            raise ValueError("Category must have at least one keyword")

    def matches(self, text: str) -> bool:
        """Проверяет, соответствует ли текст категории."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ReadingTime:
    """Value Object для времени чтения."""
    minutes: int

    def __post_init__(self):
        if self.minutes < 0:
            raise ValueError("Reading time cannot be negative")

    @classmethod
    def from_word_count(cls, word_count: int, words_per_minute: int = 200) -> 'ReadingTime':
        """Создает время чтения на основе количества слов."""
        minutes = max(1, word_count // words_per_minute)
        return cls(minutes=minutes)

    def __str__(self) -> str:
        return f"{self.minutes} мин"


@dataclass(frozen=True)
class WordCount:
    """Value Object для количества слов."""
    count: int

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("Word count cannot be negative")

    @classmethod
    def from_text(cls, text: str) -> 'WordCount':
        """Создает количество слов на основе текста."""
        if not text:
            return cls(count=0)
        
        words = re.findall(r'\b\w+\b', text.lower())
        return cls(count=len(words))

    def __str__(self) -> str:
        return str(self.count)
