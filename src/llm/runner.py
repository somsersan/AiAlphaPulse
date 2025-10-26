"""CLI for running LLM analysis of news clusters"""
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

sys.path.append(str(project_root))

from src.database import get_db_connection
from src.llm.processor import LLMNewsProcessor


def main():
    parser = argparse.ArgumentParser(
        description='LLM analysis of news clusters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Process 10 clusters on GPT-3.5-turbo
  python -m src.llm.runner --limit 10
  
  # Process 5 clusters on Claude
  python -m src.llm.runner --limit 5 --model anthropic/claude-3-haiku
  
  # Show top hot news
  python -m src.llm.runner --show-top 10
  
  # Process all unprocessed
  python -m src.llm.runner --limit 100
        """
    )
    
    parser.add_argument('--limit', type=int, default=10,
                        help='Number of clusters to process (default: 10)')
    parser.add_argument('--model', default=None,
                        help='Model to use (default: from LLM_MODEL or deepseek/deepseek-chat)')
    parser.add_argument('--delay', type=float, default=float(os.getenv('LLM_DELAY', '1.0')),
                        help='Delay between requests in seconds (default: from LLM_DELAY or 1.0)')
    parser.add_argument('--api-key', 
                        help='OpenRouter API key (or use OPENROUTER_API_KEY)')
    parser.add_argument('--show-top', type=int, metavar='N',
                        help='Show top N hottest news')
    parser.add_argument('--min-hotness', type=float, default=0.7,
                        help='Minimum hotness for top (default: 0.7)')
    
    args = parser.parse_args()
    
    # Check API key
    api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key and not args.show_top:
        print("❌ Error: set OPENROUTER_API_KEY or use --api-key")
        print("\nExample:")
        print("  export OPENROUTER_API_KEY='your-key-here'")
        print("  python -m src.llm.runner --limit 5")
        sys.exit(1)
    
    # Connect to DB
    db_conn = get_db_connection()
    db_conn.connect()
    
    try:
        # Create processor
        processor = LLMNewsProcessor(
            conn=db_conn._connection,
            api_key=api_key,
            model=args.model
        )
        
        if args.show_top:
            # Show top hot news
            print(f"\n{'='*60}")
            print(f"🔥 TOP {args.show_top} HOTTEST NEWS")
            print(f"{'='*60}\n")
            
            hot_news = processor.get_top_hot_news(
                limit=args.show_top,
                min_hotness=args.min_hotness
            )
            
            if not hot_news:
                print("📭 No news with required hotness")
            else:
                for i, news in enumerate(hot_news, 1):
                    print(f"{i}. {news['headline'][:70]}...")
                    print(f"   🔥 Hotness: {news['ai_hotness']:.3f}")
                    print(f"   📊 Tickers: {', '.join(news['tickers']) if news['tickers'] else 'N/A'}")
                    print(f"   🕒 Time: {news['published_time']}")
                    print(f"   🔗 URLs: {len(news['urls'])}")
                    print()
        else:
            # Process clusters
            print(f"\n{'='*60}")
            print(f"🤖 LLM NEWS CLUSTER ANALYSIS")
            print(f"{'='*60}")
            print(f"🎯 Model: {args.model}")
            print(f"📊 Limit: {args.limit}")
            print(f"⏱️  Delay: {args.delay}s")
            print(f"{'='*60}\n")
            
            stats = processor.process_batch(
                limit=args.limit,
                delay=args.delay
            )
            
            print(f"\n✅ Processing complete!")
            
    finally:
        db_conn.close()


if __name__ == "__main__":
    main()

