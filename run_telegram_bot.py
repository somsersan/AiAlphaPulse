#!/usr/bin/env python3
"""
Запуск Telegram бота для новостей
"""
import sys
import argparse
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.telegram.bot import NewsBot
from src.telegram.hot_news_monitor import HotNewsMonitor


def main():
    parser = argparse.ArgumentParser(
        description='Telegram бот для финансовых новостей',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Запуск бота (интерактивный режим)
  python3 run_telegram_bot.py
  
  # Запуск только монитора горячих новостей
  python3 run_telegram_bot.py --monitor-only
  
  # С кастомным порогом hotness
  python3 run_telegram_bot.py --monitor-only --threshold 0.8
  
  # С кастомным интервалом проверки
  python3 run_telegram_bot.py --monitor-only --interval 30

Перед запуском:
  1. Получите токен бота от @BotFather
  2. Добавьте в .env:
     TELEGRAM_BOT_TOKEN=ваш-токен
     TELEGRAM_CHAT_ID=ваш-chat-id
        """
    )
    
    parser.add_argument('--monitor-only', action='store_true',
                        help='Запустить только монитор горячих новостей')
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='Порог hotness для уведомлений (default: 0.7)')
    parser.add_argument('--interval', type=int, default=60,
                        help='Интервал проверки в секундах (default: 60)')
    
    args = parser.parse_args()
    
    try:
        if args.monitor_only:
            # Запуск только монитора
            print("="*60)
            print("🔍 МОНИТОР ГОРЯЧИХ НОВОСТЕЙ")
            print("="*60)
            
            monitor = HotNewsMonitor(
                hotness_threshold=args.threshold,
                check_interval=args.interval
            )
            
            asyncio.run(monitor.run())
            
        else:
            # Запуск полного бота
            print("="*60)
            print("🤖 TELEGRAM БОТ ЗАПУЩЕН")
            print("="*60)
            print("Команды:")
            print("  /start - начало работы")
            print("  /top [N] [hours] - топ новостей")
            print("  /latest [N] - последние новости")
            print("  /subscribe - подписаться на уведомления")
            print("  /help - справка")
            print("="*60)
            
            bot = NewsBot(
                enable_monitor=True,
                hotness_threshold=args.threshold,
                check_interval=args.interval
            )
            bot.run()
            
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("\nДобавьте в .env файл:")
        print("  TELEGRAM_BOT_TOKEN=ваш-токен-от-BotFather")
        print("  TELEGRAM_CHAT_ID=ваш-chat-id")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка бота...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

