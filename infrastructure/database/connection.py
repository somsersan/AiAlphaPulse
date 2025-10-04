"""
Управление подключением к базе данных.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from config.settings import settings
from infrastructure.database.models import Base
import time


class DatabaseConnection:
    """Класс для управления подключением к базе данных."""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_connection()

    def _setup_connection(self):
        """Настраивает подключение к базе данных."""
        self.engine = create_engine(
            settings.database.url,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Создает все таблицы в базе данных."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Возвращает сессию базы данных."""
        return self.SessionLocal()

    def close(self):
        """Закрывает подключение к базе данных."""
        if self.engine:
            self.engine.dispose()

    @staticmethod
    def wait_for_database(max_retries: int = 30) -> bool:
        """Ждет, пока база данных станет доступной."""
        print("🔄 Ожидание подключения к базе данных...")
        
        for attempt in range(max_retries):
            try:
                engine = create_engine(settings.database.url)
                with engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("SELECT 1"))
                print("✅ База данных доступна!")
                return True
            except OperationalError as e:
                print(f"   Попытка {attempt + 1}/{max_retries}: {e}")
                time.sleep(2)
        
        print("❌ Не удалось подключиться к базе данных")
        return False


# Глобальный экземпляр подключения
db_connection = DatabaseConnection()
