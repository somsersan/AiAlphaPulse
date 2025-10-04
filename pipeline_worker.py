#!/usr/bin/env python3
"""
Воркер для непрерывной обработки новостей:
Нормализация → Дедупликация → LLM анализ

Запускается в Docker-контейнере и работает круглосуточно
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent))

from src.database import get_db_connection
from src.normalization.process_articles import ArticleProcessor
from src.dedup.logic import process_new_batch
from src.dedup.schema import init as init_dedup
from src.llm.processor import LLMNewsProcessor


class PipelineWorker:
    """Воркер для непрерывной обработки пайплайна"""
    
    def __init__(self):
        self.check_interval = int(os.getenv('PIPELINE_CHECK_INTERVAL', '300'))  # 5 минут по умолчанию
        self.batch_size = int(os.getenv('PIPELINE_BATCH_SIZE', '100'))
        self.llm_limit = int(os.getenv('PIPELINE_LLM_LIMIT', '50'))
        self.llm_delay = float(os.getenv('LLM_DELAY', '1.0'))
        self.llm_model = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat')
        
        self.normalizer = ArticleProcessor()
        self.db_conn = get_db_connection()
        
        print("="*60)
        print("🚀 PIPELINE WORKER")
        print("="*60)
        print(f"📊 Интервал проверки: {self.check_interval}с")
        print(f"📦 Размер батча: {self.batch_size}")
        print(f"🤖 LLM лимит: {self.llm_limit}")
        print(f"⏱️  LLM задержка: {self.llm_delay}с")
        print(f"🎯 LLM модель: {self.llm_model}")
        print("="*60)
    
    def run_normalization(self) -> int:
        """Запуск нормализации новых статей"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📝 Нормализация...")
        
        try:
            self.normalizer.connect_db()
            status = self.normalizer.get_processing_status()
            
            if status['is_up_to_date']:
                print("   ✅ Нет новых статей для нормализации")
                return 0
            
            print(f"   📊 Необработано: {status['unprocessed_count']}")
            articles = self.normalizer.load_unprocessed_articles(limit=self.batch_size)
            
            if not articles:
                print("   ✅ Нет статей для обработки")
                return 0
            
            stats = self.normalizer.process_articles_batch(articles, self.batch_size)
            print(f"   ✅ Обработано: {stats['processed_articles']}, Отфильтровано: {stats['filtered_articles']}")
            
            return stats['processed_articles']
            
        except Exception as e:
            print(f"   ❌ Ошибка нормализации: {e}")
            return 0
        finally:
            self.normalizer.close_db()
    
    def run_deduplication(self) -> int:
        """Запуск дедупликации"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 Дедупликация...")
        
        try:
            self.db_conn.connect()
            init_dedup(self.db_conn._connection)
            
            n = process_new_batch(self.db_conn._connection, k_neighbors=30)
            print(f"   ✅ Обработано записей: {n}")
            
            return n
            
        except Exception as e:
            print(f"   ❌ Ошибка дедупликации: {e}")
            return 0
        finally:
            self.db_conn.close()
    
    def run_llm_analysis(self) -> int:
        """Запуск LLM анализа новых кластеров"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🤖 LLM анализ...")
        
        try:
            self.db_conn.connect()
            
            processor = LLMNewsProcessor(
                conn=self.db_conn._connection,
                model=self.llm_model
            )
            
            stats = processor.process_batch(
                limit=self.llm_limit,
                delay=self.llm_delay
            )
            
            print(f"   ✅ Обработано: {stats['processed']}, Пропущено: {stats['skipped']}, Ошибок: {stats['errors']}")
            
            return stats['processed']
            
        except Exception as e:
            print(f"   ❌ Ошибка LLM анализа: {e}")
            return 0
        finally:
            self.db_conn.close()
    
    def run_cycle(self):
        """Один цикл обработки"""
        print(f"\n{'='*60}")
        print(f"🔄 НАЧАЛО ЦИКЛА: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        total_start = time.time()
        
        # Шаг 1: Нормализация
        normalized_count = self.run_normalization()
        
        # Шаг 2: Дедупликация (если были нормализованы новые статьи)
        dedup_count = 0
        if normalized_count > 0:
            dedup_count = self.run_deduplication()
        else:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏭️  Пропуск дедупликации (нет новых статей)")
        
        # Шаг 3: LLM анализ (если были созданы новые кластеры)
        llm_count = 0
        if dedup_count > 0 or normalized_count > 0:
            llm_count = self.run_llm_analysis()
        else:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏭️  Пропуск LLM анализа (нет новых кластеров)")
        
        total_time = time.time() - total_start
        
        print(f"\n{'='*60}")
        print(f"✅ ЦИКЛ ЗАВЕРШЕН: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Время: {total_time:.1f}с")
        print(f"📊 Результаты:")
        print(f"   • Нормализовано: {normalized_count}")
        print(f"   • Дедуплицировано: {dedup_count}")
        print(f"   • LLM проанализировано: {llm_count}")
        print(f"{'='*60}")
    
    def run(self):
        """Главный цикл воркера"""
        print(f"\n🚀 Воркер запущен в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ Следующая проверка через {self.check_interval}с\n")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                print(f"\n{'#'*60}")
                print(f"# ЦИКЛ #{cycle_count}")
                print(f"{'#'*60}")
                
                self.run_cycle()
                
                print(f"\n💤 Ожидание {self.check_interval}с до следующей проверки...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Остановка воркера по Ctrl+C...")
                break
            except Exception as e:
                print(f"\n❌ Критическая ошибка в цикле: {e}")
                import traceback
                traceback.print_exc()
                print(f"\n💤 Ожидание {self.check_interval}с перед повтором...")
                time.sleep(self.check_interval)


def main():
    """Точка входа"""
    try:
        worker = PipelineWorker()
        worker.run()
    except Exception as e:
        print(f"\n❌ Критическая ошибка запуска: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

