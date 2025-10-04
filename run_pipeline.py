#!/usr/bin/env python3
"""
Главный скрипт для автоматического запуска пайплайна обработки новостей:
1. Парсинг (через API) или ожидание новых статей
2. Нормализация
3. Дедупликация
4. Экспорт топовых кластеров

Запускается в цикле с настраиваемым интервалом.
"""

import time
import argparse
import sys
import requests
from datetime import datetime
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent))

from src.normalization.process_articles import ArticleProcessor
from src.dedup.logic import process_new_batch
from src.dedup.export_topk import export_topk
from src.database import get_db_connection


class NewsPipeline:
    """Класс для управления пайплайном обработки новостей"""
    
    def __init__(self, 
                 parser_url: str = "http://localhost:8000",
                 interval_seconds: int = 300,
                 k_neighbors: int = 30,
                 top_k: int = 10,
                 window_hours: int = 48):
        self.parser_url = parser_url
        self.interval_seconds = interval_seconds
        self.k_neighbors = k_neighbors
        self.top_k = top_k
        self.window_hours = window_hours
        
        self.article_processor = ArticleProcessor()
        self.db_conn = None
        
        # Статистика
        self.stats = {
            'cycles': 0,
            'total_parsed': 0,
            'total_normalized': 0,
            'total_deduplicated': 0,
            'errors': 0
        }
    
    def check_parser_health(self) -> bool:
        """Проверка доступности парсера"""
        try:
            response = requests.get(f"{self.parser_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Парсер недоступен: {e}")
            return False
    
    def trigger_manual_parse(self) -> int:
        """Ручной запуск парсинга через API"""
        try:
            print("🔄 Запускаем ручной парсинг...")
            response = requests.post(f"{self.parser_url}/parse", timeout=300)
            if response.status_code == 200:
                data = response.json()
                new_count = data.get('new_articles_count', 0)
                print(f"✅ Парсинг завершен. Добавлено статей: {new_count}")
                return new_count
            else:
                print(f"❌ Ошибка парсинга: {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ Ошибка при запуске парсинга: {e}")
            return 0
    
    def run_normalization(self) -> dict:
        """Запуск нормализации необработанных статей"""
        try:
            print("\n" + "="*60)
            print("📝 ЭТАП 2: НОРМАЛИЗАЦИЯ")
            print("="*60)
            
            self.article_processor.connect_db()
            
            # Показываем статус
            status = self.article_processor.get_processing_status()
            print(f"📊 Статус:")
            print(f"   - Всего статей: {status['total_articles']}")
            print(f"   - Обработано: {status['processed_count']}")
            print(f"   - Необработано: {status['unprocessed_count']}")
            
            if status['is_up_to_date']:
                print("✅ Все статьи уже нормализованы")
                return {'processed_articles': 0}
            
            # Обрабатываем необработанные статьи
            articles = self.article_processor.load_unprocessed_articles()
            if not articles:
                print("ℹ️  Нет новых статей для нормализации")
                return {'processed_articles': 0}
            
            print(f"📝 Нормализуем {len(articles)} статей...")
            result = self.article_processor.process_articles_batch(articles)
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка нормализации: {e}")
            import traceback
            traceback.print_exc()
            return {'processed_articles': 0, 'error': str(e)}
        finally:
            self.article_processor.close_db()
    
    def run_deduplication(self) -> int:
        """Запуск дедупликации"""
        try:
            print("\n" + "="*60)
            print("🔗 ЭТАП 3: ДЕДУПЛИКАЦИЯ И КЛАСТЕРИЗАЦИЯ")
            print("="*60)
            
            self.db_conn = get_db_connection()
            self.db_conn.connect()
            
            # Инициализируем таблицы дедупликации
            from src.dedup.schema import init
            init(self.db_conn._connection)
            
            # Запускаем дедупликацию
            print(f"🔍 Обрабатываем новые статьи (k_neighbors={self.k_neighbors})...")
            n = process_new_batch(self.db_conn._connection, self.k_neighbors)
            
            print(f"✅ Обработано записей: {n}")
            return n
            
        except Exception as e:
            print(f"❌ Ошибка дедупликации: {e}")
            import traceback
            traceback.print_exc()
            return 0
        finally:
            if self.db_conn:
                self.db_conn.close()
    
    def export_results(self) -> bool:
        """Экспорт топовых кластеров"""
        try:
            print("\n" + "="*60)
            print("📤 ЭТАП 4: ЭКСПОРТ РЕЗУЛЬТАТОВ")
            print("="*60)
            
            output_file = "radar_top.json"
            print(f"📊 Экспортируем топ-{self.top_k} кластеров за {self.window_hours}ч...")
            
            export_topk(output_file, self.top_k, self.window_hours)
            
            print(f"✅ Результаты сохранены в {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_cycle(self) -> dict:
        """Запуск одного цикла пайплайна"""
        cycle_start = time.time()
        
        print("\n" + "="*60)
        print(f"🚀 ЗАПУСК ЦИКЛА #{self.stats['cycles'] + 1}")
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        cycle_stats = {
            'parsed': 0,
            'normalized': 0,
            'deduplicated': 0,
            'exported': False,
            'duration': 0
        }
        
        try:
            # ЭТАП 1: Проверка парсера (парсер работает автоматически в фоне)
            print("\n" + "="*60)
            print("📰 ЭТАП 1: ПАРСИНГ (автоматический)")
            print("="*60)
            
            if self.check_parser_health():
                print("✅ Парсер работает в фоновом режиме")
                # Можно опционально запустить ручной парсинг
                # cycle_stats['parsed'] = self.trigger_manual_parse()
            else:
                print("⚠️ Парсер недоступен, продолжаем с существующими данными")
            
            # ЭТАП 2: Нормализация
            norm_result = self.run_normalization()
            cycle_stats['normalized'] = norm_result.get('processed_articles', 0)
            
            # ЭТАП 3: Дедупликация
            if cycle_stats['normalized'] > 0:
                cycle_stats['deduplicated'] = self.run_deduplication()
            else:
                print("\n⏭️  Пропускаем дедупликацию (нет новых нормализованных статей)")
            
            # ЭТАП 4: Экспорт
            if cycle_stats['deduplicated'] > 0:
                cycle_stats['exported'] = self.export_results()
            else:
                print("\n⏭️  Пропускаем экспорт (нет новых кластеров)")
            
            # Обновляем общую статистику
            self.stats['cycles'] += 1
            self.stats['total_parsed'] += cycle_stats['parsed']
            self.stats['total_normalized'] += cycle_stats['normalized']
            self.stats['total_deduplicated'] += cycle_stats['deduplicated']
            
        except Exception as e:
            print(f"\n❌ Ошибка в цикле: {e}")
            self.stats['errors'] += 1
            import traceback
            traceback.print_exc()
        
        cycle_stats['duration'] = time.time() - cycle_start
        
        # Итоги цикла
        print("\n" + "="*60)
        print("📊 ИТОГИ ЦИКЛА")
        print("="*60)
        print(f"⏱️  Длительность: {cycle_stats['duration']:.1f} секунд")
        print(f"📝 Нормализовано: {cycle_stats['normalized']}")
        print(f"🔗 Дедуплицировано: {cycle_stats['deduplicated']}")
        print(f"📤 Экспорт: {'✅' if cycle_stats['exported'] else '⏭️'}")
        
        print("\n" + "="*60)
        print("📈 ОБЩАЯ СТАТИСТИКА")
        print("="*60)
        print(f"🔄 Всего циклов: {self.stats['cycles']}")
        print(f"📝 Всего нормализовано: {self.stats['total_normalized']}")
        print(f"🔗 Всего дедуплицировано: {self.stats['total_deduplicated']}")
        print(f"❌ Ошибок: {self.stats['errors']}")
        
        return cycle_stats
    
    def run_continuous(self):
        """Непрерывный запуск пайплайна с интервалами"""
        print("="*60)
        print("🎯 ЗАПУСК АВТОМАТИЧЕСКОГО ПАЙПЛАЙНА")
        print("="*60)
        print(f"📡 Парсер: {self.parser_url}")
        print(f"⏱️  Интервал: {self.interval_seconds} секунд")
        print(f"🔍 K-neighbors: {self.k_neighbors}")
        print(f"📊 Top-K: {self.top_k}")
        print(f"🕒 Окно: {self.window_hours} часов")
        print("="*60)
        print("\nНажмите Ctrl+C для остановки\n")
        
        try:
            while True:
                self.run_cycle()
                
                print(f"\n⏳ Ожидание {self.interval_seconds} секунд до следующего цикла...")
                print(f"⏰ Следующий запуск: {datetime.fromtimestamp(time.time() + self.interval_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
                
                time.sleep(self.interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Остановка пайплайна...")
            print("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
            print(f"   Всего циклов: {self.stats['cycles']}")
            print(f"   Нормализовано: {self.stats['total_normalized']}")
            print(f"   Дедуплицировано: {self.stats['total_deduplicated']}")
            print(f"   Ошибок: {self.stats['errors']}")
            print("\n✅ Пайплайн остановлен")


def main():
    parser = argparse.ArgumentParser(
        description='Автоматический пайплайн обработки новостей',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Запуск с интервалом 5 минут (по умолчанию)
  python run_pipeline.py

  # Запуск с интервалом 10 минут
  python run_pipeline.py --interval 600

  # Однократный запуск
  python run_pipeline.py --once

  # С кастомными параметрами
  python run_pipeline.py --interval 300 --k-neighbors 50 --top-k 20
        """
    )
    
    parser.add_argument('--parser-url', default='http://localhost:8000',
                        help='URL парсера API (default: http://localhost:8000)')
    parser.add_argument('--interval', type=int, default=300,
                        help='Интервал между циклами в секундах (default: 300 = 5 минут)')
    parser.add_argument('--k-neighbors', type=int, default=30,
                        help='Количество соседей для дедупликации (default: 30)')
    parser.add_argument('--top-k', type=int, default=10,
                        help='Количество топовых кластеров для экспорта (default: 10)')
    parser.add_argument('--window-hours', type=int, default=48,
                        help='Временное окно для экспорта в часах (default: 48)')
    parser.add_argument('--once', action='store_true',
                        help='Запустить только один цикл и выйти')
    
    args = parser.parse_args()
    
    # Создаем пайплайн
    pipeline = NewsPipeline(
        parser_url=args.parser_url,
        interval_seconds=args.interval,
        k_neighbors=args.k_neighbors,
        top_k=args.top_k,
        window_hours=args.window_hours
    )
    
    # Запускаем
    if args.once:
        print("🎯 Режим: однократный запуск\n")
        pipeline.run_cycle()
    else:
        print("🎯 Режим: непрерывный запуск\n")
        pipeline.run_continuous()


if __name__ == "__main__":
    main()

