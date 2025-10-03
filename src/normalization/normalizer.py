"""
Модуль для нормализации и очистки данных новостей
"""
import re
import html
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import langdetect
from langdetect import detect
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import unicodedata


class NewsNormalizer:
    """Класс для нормализации новостных данных"""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.spam_patterns = [
            r'реклама',
            r'спонсор',
            r'партнер',
            r'купить\s+сейчас',
            r'скидка\s+\d+%',
            r'только\s+сегодня',
            r'ограниченное\s+предложение',
            r'кликните\s+здесь',
            r'подробнее\s+на\s+сайте',
            r'перейти\s+по\s+ссылке'
        ]
        
        # Инициализация NLTK данных
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
    
    def clean_html(self, text: str) -> str:
        """Очистка HTML тегов и декодирование HTML entities"""
        if not text:
            return ""
        
        # Декодирование HTML entities
        text = html.unescape(text)
        
        # Удаление HTML тегов
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        
        # Нормализация пробелов
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def detect_language(self, text: str) -> str:
        """Определение языка текста"""
        if not text or len(text.strip()) < 10:
            return 'unknown'
        
        try:
            # Берем первые 1000 символов для определения языка
            sample_text = text[:1000]
            language = detect(sample_text)
            return language
        except:
            return 'unknown'
    
    def is_spam(self, text: str) -> bool:
        """Проверка на спам по паттернам"""
        if not text:
            return True
        
        text_lower = text.lower()
        
        # Проверка длины
        if len(text.strip()) < 50:
            return True
        
        # Проверка спам-паттернов
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Проверка на слишком много эмодзи
        emoji_count = len(re.findall(r'[😀-🙏🌀-🗿]', text))
        if emoji_count > len(text) * 0.1:  # Более 10% эмодзи
            return True
        
        return False
    
    def normalize_text(self, text: str) -> str:
        """Нормализация текста: очистка, лемматизация"""
        if not text:
            return ""
        
        # Очистка HTML
        text = self.clean_html(text)
        
        # Нормализация Unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Удаление лишних символов, но сохранение пунктуации
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        
        # Нормализация пробелов
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_entities(self, text: str) -> List[str]:
        """Простое извлечение сущностей (компании, тикеры, страны)"""
        entities = []
        
        # Паттерны для тикеров (заглавные буквы, 2-5 символов)
        tickers = re.findall(r'\b[A-Z]{2,5}\b', text)
        entities.extend(tickers)
        
        # Паттерны для компаний (с заглавной буквы)
        companies = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.extend(companies)
        
        # Удаление дубликатов и сортировка
        entities = list(set(entities))
        entities.sort()
        
        return entities[:20]  # Ограничиваем количество
    
    def calculate_quality_score(self, article: Dict) -> float:
        """Расчет качества статьи (0-1)"""
        score = 0.0
        
        # Проверка наличия контента
        if not article.get('content') or len(article['content'].strip()) < 100:
            return 0.0
        
        # Длина контента
        content_length = len(article['content'])
        if content_length > 500:
            score += 0.3
        elif content_length > 200:
            score += 0.2
        
        # Наличие заголовка
        if article.get('title') and len(article['title'].strip()) > 10:
            score += 0.2
        
        # Наличие ссылки
        if article.get('link'):
            score += 0.1
        
        # Наличие источника
        if article.get('source'):
            score += 0.1
        
        # Проверка на спам
        if not self.is_spam(article.get('content', '')):
            score += 0.3
        else:
            score *= 0.3  # Сильно снижаем оценку за спам
        
        return min(score, 1.0)
    
    def normalize_article(self, article: Dict) -> Optional[Dict]:
        """Нормализация одной статьи"""
        # Проверка на спам
        if self.is_spam(article.get('content', '')):
            return None
        
        # Очистка и нормализация текста
        normalized_content = self.normalize_text(article.get('content', ''))
        normalized_title = self.normalize_text(article.get('title', ''))
        
        if not normalized_content or len(normalized_content.strip()) < 50:
            return None
        
        # Определение языка
        language = self.detect_language(normalized_content)
        
        # Извлечение сущностей
        entities = self.extract_entities(normalized_content)
        
        # Расчет качества
        quality_score = self.calculate_quality_score(article)
        
        if quality_score < 0.3:  # Минимальный порог качества
            return None
        
        # Создание нормализованной записи
        normalized_article = {
            'original_id': article.get('id'),
            'title': normalized_title,
            'content': normalized_content,
            'link': article.get('link'),
            'source': article.get('source'),
            'published_at': article.get('published'),
            'language_code': language,
            'entities': entities,
            'quality_score': quality_score,
            'word_count': len(normalized_content.split()),
            'is_processed': True
        }
        
        return normalized_article
