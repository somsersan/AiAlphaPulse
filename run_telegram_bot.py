#!/usr/bin/env python3
"""
Launch Telegram bot for news
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
        description='Telegram bot for financial news',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:

  # Launch bot (interactive mode)
  python3 run_telegram_bot.py
  
  # Launch only hot news monitor
  python3 run_telegram_bot.py --monitor-only
  
  # With custom hotness threshold
  python3 run_telegram_bot.py --monitor-only --threshold 0.8
  
  # With custom check interval
  python3 run_telegram_bot.py --monitor-only --interval 30

Before launch:
  1. Get bot token from @BotFather
  2. Add to .env:
     TELEGRAM_BOT_TOKEN=your-token
     TELEGRAM_CHAT_ID=your-chat-id
        """
    )
    
    parser.add_argument('--monitor-only', action='store_true',
                        help='Launch only hot news monitor')
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='Hotness threshold for notifications (default: 0.7)')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    try:
        if args.monitor_only:
            # Launch monitor only
            print("="*60)
            print("🔍 HOT NEWS MONITOR")
            print("="*60)
            
            monitor = HotNewsMonitor(
                hotness_threshold=args.threshold,
                check_interval=args.interval
            )
            
            asyncio.run(monitor.run())
            
        else:
            # Launch full bot
            print("="*60)
            print("🤖 TELEGRAM BOT STARTED")
            print("="*60)
            print("Commands:")
            print("  /start - start working")
            print("  /top [N] [hours] - top news")
            print("  /latest [N] - latest news")
            print("  /subscribe - subscribe to notifications")
            print("  /help - help")
            print("="*60)
            
            bot = NewsBot(
                enable_monitor=True,
                hotness_threshold=args.threshold,
                check_interval=args.interval
            )
            bot.run()
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nAdd to .env file:")
        print("  TELEGRAM_BOT_TOKEN=your-token-from-BotFather")
        print("  TELEGRAM_CHAT_ID=your-chat-id")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping bot...")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

