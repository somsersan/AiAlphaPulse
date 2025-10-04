"""CLI для запуска LLM анализа новостных кластеров"""
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env файл из корня проекта
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

sys.path.append(str(project_root))

from src.database import get_db_connection
from src.llm.processor import LLMNewsProcessor


def main():
    parser = argparse.ArgumentParser(
        description='LLM анализ новостных кластеров',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Обработать 10 кластеров на GPT-3.5-turbo
  python -m src.llm.runner --limit 10
  
  # Обработать 5 кластеров на Claude
  python -m src.llm.runner --limit 5 --model anthropic/claude-3-haiku
  
  # Показать топ горячих новостей
  python -m src.llm.runner --show-top 10
  
  # Обработать все необработанные
  python -m src.llm.runner --limit 100
        """
    )
    
    parser.add_argument('--limit', type=int, default=10,
                        help='Количество кластеров для обработки (default: 10)')
    parser.add_argument('--model', default=None,
                        help='Модель для использования (default: из LLM_MODEL или deepseek/deepseek-chat)')
    parser.add_argument('--delay', type=float, default=float(os.getenv('LLM_DELAY', '1.0')),
                        help='Задержка между запросами в секундах (default: из LLM_DELAY или 1.0)')
    parser.add_argument('--api-key', 
                        help='OpenRouter API ключ (или используйте OPENROUTER_API_KEY)')
    parser.add_argument('--show-top', type=int, metavar='N',
                        help='Показать топ N самых горячих новостей')
    parser.add_argument('--min-hotness', type=float, default=0.7,
                        help='Минимальная горячность для топа (default: 0.7)')
    
    args = parser.parse_args()
    
    # Проверяем API ключ
    api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key and not args.show_top:
        print("❌ Ошибка: установите OPENROUTER_API_KEY или используйте --api-key")
        print("\nПример:")
        print("  export OPENROUTER_API_KEY='your-key-here'")
        print("  python -m src.llm.runner --limit 5")
        sys.exit(1)
    
    # Подключаемся к БД
    db_conn = get_db_connection()
    db_conn.connect()
    
    try:
        # Создаем процессор
        processor = LLMNewsProcessor(
            conn=db_conn._connection,
            api_key=api_key,
            model=args.model
        )
        
        if args.show_top:
            # Показываем топ горячих новостей
            print(f"\n{'='*60}")
            print(f"🔥 ТОП-{args.show_top} САМЫХ ГОРЯЧИХ НОВОСТЕЙ")
            print(f"{'='*60}\n")
            
            hot_news = processor.get_top_hot_news(
                limit=args.show_top,
                min_hotness=args.min_hotness
            )
            
            if not hot_news:
                print("📭 Нет новостей с требуемой горячностью")
            else:
                for i, news in enumerate(hot_news, 1):
                    print(f"{i}. {news['headline'][:70]}...")
                    print(f"   🔥 Hotness: {news['ai_hotness']:.3f}")
                    print(f"   📊 Tickers: {', '.join(news['tickers']) if news['tickers'] else 'N/A'}")
                    print(f"   🕒 Time: {news['published_time']}")
                    print(f"   🔗 URLs: {len(news['urls'])}")
                    print()
        else:
            # Обрабатываем кластеры
            print(f"\n{'='*60}")
            print(f"🤖 LLM АНАЛИЗ НОВОСТНЫХ КЛАСТЕРОВ")
            print(f"{'='*60}")
            print(f"🎯 Модель: {args.model}")
            print(f"📊 Лимит: {args.limit}")
            print(f"⏱️  Задержка: {args.delay}с")
            print(f"{'='*60}\n")
            
            stats = processor.process_batch(
                limit=args.limit,
                delay=args.delay
            )
            
            print(f"\n✅ Обработка завершена!")
            
    finally:
        db_conn.close()


if __name__ == "__main__":
    main()

