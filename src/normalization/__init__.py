"""
Модуль нормализации новостных данных
"""
from .normalizer import NewsNormalizer
from .database_schema import (
    create_normalized_articles_table,
    create_processing_log_table,
    get_processed_articles,
    get_max_processed_id,
    get_unprocessed_articles,
    insert_normalized_article,
    log_processing_batch,
    get_processing_stats
)
from .process_articles import ArticleProcessor
from .export_to_json import export_normalized_to_json

__all__ = [
    'NewsNormalizer',
    'ArticleProcessor',
    'export_normalized_to_json',
    'create_normalized_articles_table',
    'create_processing_log_table',
    'get_processed_articles',
    'get_max_processed_id',
    'get_unprocessed_articles',
    'insert_normalized_article',
    'log_processing_batch',
    'get_processing_stats'
]
