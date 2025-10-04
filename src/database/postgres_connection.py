"""
Модуль для подключения к PostgreSQL
"""
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Optional, Dict, Any
import os


class PostgreSQLConnection:
    """Класс для работы с PostgreSQL"""
    
    def __init__(self, 
                 host: str = "51.250.17.41",
                 port: int = 5432,
                 database: str = "alphapulse", 
                 user: str = "admin",
                 password: str = "04102025"):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self._connection = None
    
    def connect(self):
        """Подключение к базе данных"""
        try:
            self._connection = psycopg2.connect(**self.connection_params)
            self._connection.autocommit = False
            return self._connection
        except psycopg2.OperationalError as e:
            raise Exception(f"Ошибка подключения к PostgreSQL: {e}")
        except psycopg2.Error as e:
            raise Exception(f"Ошибка PostgreSQL: {e}")
        except Exception as e:
            raise Exception(f"Неожиданная ошибка: {e}")
    
    def close(self):
        """Закрытие соединения"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Контекстный менеджер для работы с курсором"""
        if not self._connection:
            self.connect()
        
        cursor_class = psycopg2.extras.RealDictCursor if dict_cursor else psycopg2.extras.DictCursor
        cursor = self._connection.cursor(cursor_factory=cursor_class)
        
        try:
            yield cursor
        except Exception as e:
            self._connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = None):
        """Выполнение запроса"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            elif fetch == 'many':
                return cursor.fetchmany()
            else:
                self._connection.commit()
                return cursor.rowcount
    
    def create_tables(self):
        """Создание всех таблиц"""
        from .postgres_schema import create_all_tables
        create_all_tables(self._connection)


# Глобальный экземпляр для использования в приложении
db_connection = PostgreSQLConnection()


def get_db_connection() -> PostgreSQLConnection:
    """Получить подключение к базе данных"""
    return db_connection


@contextmanager
def get_db_cursor():
    """Контекстный менеджер для получения курсора базы данных"""
    with db_connection.get_cursor() as cursor:
        yield cursor
