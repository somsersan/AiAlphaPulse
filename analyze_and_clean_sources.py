"""
Скрипт для анализа источников в таблице articles и удаления некриптовалютных источников
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.postgres_connection import PostgreSQLConnection

def analyze_sources():
    """Анализирует источники в таблице articles"""
    db = PostgreSQLConnection()
    db.connect()
    
    try:
        with db.get_cursor() as cursor:
            # Проверяем, какая таблица существует
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (table_name = 'articles' OR table_name = 'financial_news_view')
            """)
            tables = cursor.fetchall()
            
            if not tables:
                print("❌ Таблицы articles или financial_news_view не найдены!")
                return
            
            table_name = None
            for table in tables:
                if table['table_name'] == 'financial_news_view':
                    table_name = 'financial_news_view'
                    break
                elif table['table_name'] == 'articles':
                    table_name = 'articles'
            
            if not table_name:
                print("❌ Не найдена подходящая таблица!")
                return
            
            print(f"✅ Используем таблицу: {table_name}")
            
            # Получаем статистику по источникам
            cursor.execute(f"""
                SELECT 
                    source,
                    COUNT(*) as count,
                    MIN(published) as first_article,
                    MAX(published) as last_article
                FROM {table_name}
                GROUP BY source
                ORDER BY count DESC
            """)
            
            sources = cursor.fetchall()
            
            print(f"\n📊 Найдено источников: {len(sources)}")
            print("\n" + "="*80)
            print("СТАТИСТИКА ПО ИСТОЧНИКАМ:")
            print("="*80)
            
            for source_info in sources:
                source = source_info['source']
                count = source_info['count']
                print(f"\n📰 Источник: {source}")
                print(f"   Статей: {count}")
                if source_info['first_article']:
                    print(f"   Первая статья: {source_info['first_article']}")
                    print(f"   Последняя статья: {source_info['last_article']}")
            
            # Получаем примеры статей от каждого источника
            print("\n" + "="*80)
            print("ПРИМЕРЫ СТАТЕЙ ОТ КАЖДОГО ИСТОЧНИКА:")
            print("="*80)
            
            for source_info in sources:
                source = source_info['source']
                cursor.execute(f"""
                    SELECT title, link, published
                    FROM {table_name}
                    WHERE source = %s
                    ORDER BY published DESC
                    LIMIT 3
                """, (source,))
                
                articles = cursor.fetchall()
                print(f"\n📰 {source} ({len(articles)} примеров):")
                for article in articles:
                    title = article['title'][:60] + "..." if len(article['title']) > 60 else article['title']
                    print(f"   - {title}")
            
            return sources, table_name
            
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()


def identify_non_crypto_sources(sources):
    """Определяет источники, не связанные с криптовалютой"""
    
    # Ключевые слова, связанные с криптовалютой
    crypto_keywords = [
        'crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'blockchain',
        'крипто', 'биткоин', 'блокчейн', 'эфириум', 'альткоин',
        'coin', 'token', 'nft', 'defi', 'dex', 'cex',
        'монета', 'токен', 'дефі', 'бирж', 'майнинг'
    ]
    
    # Источники, которые точно связаны с криптовалютой
    crypto_sources = [
        'coinbase', 'binance', 'coindesk', 'cointelegraph', 'theblock',
        'bitkogan', 'cryptomarkets', 'satoshi', 'hypercharts',
        'crypto.news', 'bitcoin news', 'bitcoin magazine', 'beincrypto',
        'decrypt', 'u.today', 'bitcoin', 'ethereum', 'crypto'
    ]
    
    # Источники, которые точно НЕ связаны с криптовалютой (общие новости)
    non_crypto_sources = [
        'lenta.ru', 'habr', 'rbc', 'vedomosti', 'kommersant', 'tass',
        'google news', 'news.google', 'news', 'новости', 'главные новости',
        'tass_agency', 'interfax', 'banksta', 'bezposhady', 'banki_economy',
        'cb_economics', 'cbonds', 'bloomeconomy', 'bloombusiness', 'bloomberg',
        'economist', 'sberbank', 'vtb', 'alfabank', 'ozon_bank', 'centralbank',
        'moneycontrol', 'frank_media', 'rbc_quote', 'rbcnews'
    ]
    
    non_crypto = []
    crypto = []
    uncertain = []
    
    for source_info in sources:
        source = source_info['source']
        source_lower = source.lower()
        
        # Проверяем по точным совпадениям
        is_crypto_source = any(crypto_word in source_lower for crypto_word in crypto_sources)
        is_non_crypto_source = any(non_word in source_lower for non_word in non_crypto_sources)
        
        if is_crypto_source:
            crypto.append(source_info)
        elif is_non_crypto_source:
            non_crypto.append(source_info)
        else:
            # Для неопределенных источников нужно проверить контент статей
            uncertain.append(source_info)
    
    return non_crypto, crypto, uncertain


def check_source_content(db, table_name, source, sample_size=10):
    """Проверяет контент статей от источника для определения тематики"""
    crypto_keywords = [
        'crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'blockchain',
        'крипто', 'биткоин', 'блокчейн', 'эфириум', 'альткоин',
        'coin', 'token', 'nft', 'defi', 'dex', 'cex',
        'монета', 'токен', 'дефі', 'бирж', 'майнинг'
    ]
    
    with db.get_cursor() as cursor:
        cursor.execute(f"""
            SELECT title, summary, content
            FROM {table_name}
            WHERE source = %s
            LIMIT %s
        """, (source, sample_size))
        
        articles = cursor.fetchall()
        
        crypto_matches = 0
        total_articles = len(articles)
        
        for article in articles:
            text = " ".join([
                article.get('title', '') or '',
                article.get('summary', '') or '',
                article.get('content', '') or ''
            ]).lower()
            
            if any(keyword in text for keyword in crypto_keywords):
                crypto_matches += 1
        
        crypto_ratio = crypto_matches / total_articles if total_articles > 0 else 0
        
        return crypto_ratio >= 0.3  # Если хотя бы 30% статей содержат крипто-ключевые слова


def clean_non_crypto_sources(table_name, sources_to_delete, dry_run=True):
    """Удаляет статьи от некриптовалютных источников"""
    db = PostgreSQLConnection()
    db.connect()
    
    # Определяем реальную таблицу для удаления (view нельзя удалять напрямую)
    actual_table = 'articles' if table_name == 'financial_news_view' else table_name
    
    try:
        with db.get_cursor() as cursor:
            # Проверяем, существует ли таблица articles
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (actual_table,))
            
            result = cursor.fetchone()
            table_exists = result['exists'] if isinstance(result, dict) else result[0]
            
            if not table_exists:
                print(f"❌ Таблица {actual_table} не найдена!")
                return
            
            total_deleted = 0
            
            for source_info in sources_to_delete:
                source = source_info['source']
                count = source_info['count']
                
                if dry_run:
                    print(f"🔍 [DRY RUN] Будет удалено {count} статей от источника: {source}")
                else:
                    cursor.execute(f"""
                        DELETE FROM {actual_table}
                        WHERE source = %s
                    """, (source,))
                    
                    deleted = cursor.rowcount
                    total_deleted += deleted
                    print(f"✅ Удалено {deleted} статей от источника: {source}")
            
            if not dry_run:
                db._connection.commit()
                print(f"\n✅ Всего удалено статей: {total_deleted}")
            else:
                print(f"\n🔍 [DRY RUN] Всего будет удалено статей: {sum(s['count'] for s in sources_to_delete)}")
                
    except Exception as e:
        print(f"❌ Ошибка при удалении: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            db._connection.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔍 Анализ источников в базе данных...")
    print("="*80)
    
    # Шаг 1: Анализ источников
    sources, table_name = analyze_sources()
    
    if not sources or not table_name:
        print("❌ Не удалось получить данные. Выход.")
        sys.exit(1)
    
    # Шаг 2: Определение некриптовалютных источников
    print("\n" + "="*80)
    print("ОПРЕДЕЛЕНИЕ НЕКРИПТОВАЛЮТНЫХ ИСТОЧНИКОВ:")
    print("="*80)
    
    non_crypto, crypto, uncertain = identify_non_crypto_sources(sources)
    
    print(f"\n✅ Криптовалютные источники ({len(crypto)}):")
    for source_info in crypto:
        print(f"   - {source_info['source']} ({source_info['count']} статей)")
    
    print(f"\n❌ Некриптовалютные источники ({len(non_crypto)}):")
    for source_info in non_crypto:
        print(f"   - {source_info['source']} ({source_info['count']} статей)")
    
    print(f"\n❓ Неопределенные источники ({len(uncertain)}):")
    
    # Шаг 3: Проверка неопределенных источников по контенту
    db = PostgreSQLConnection()
    db.connect()
    
    for source_info in uncertain:
        source = source_info['source']
        print(f"\n   🔍 Проверяю источник: {source}...")
        
        is_crypto = check_source_content(db, table_name, source, sample_size=20)
        
        if is_crypto:
            crypto.append(source_info)
            print(f"      ✅ Определен как криптовалютный")
        else:
            non_crypto.append(source_info)
            print(f"      ❌ Определен как некриптовалютный")
    
    db.close()
    
    # Финальная статистика
    print("\n" + "="*80)
    print("ИТОГОВАЯ СТАТИСТИКА:")
    print("="*80)
    
    crypto_total = sum(s['count'] for s in crypto)
    non_crypto_total = sum(s['count'] for s in non_crypto)
    
    print(f"\n✅ Криптовалютные источники: {len(crypto)} источников, {crypto_total} статей")
    print(f"❌ Некриптовалютные источники: {len(non_crypto)} источников, {non_crypto_total} статей")
    
    # Шаг 4: Удаление (сначала dry run)
    if non_crypto:
        print("\n" + "="*80)
        print("УДАЛЕНИЕ НЕКРИПТОВАЛЮТНЫХ ИСТОЧНИКОВ:")
        print("="*80)
        
        print("\n🔍 DRY RUN (проверка без удаления):")
        clean_non_crypto_sources(table_name, non_crypto, dry_run=True)
        
        print("\n" + "="*80)
        print("\n⚠️  ВНИМАНИЕ: Будет удалено {} статей от {} источников!".format(
            non_crypto_total, len(non_crypto)
        ))
        print("\nДля продолжения запустите скрипт снова и введите 'yes'")
        print("Или запустите с параметром --execute для автоматического удаления")
        
        # Автоматическое удаление если передан флаг --execute
        import sys
        if '--execute' in sys.argv:
            print("\n🗑️ Удаление статей...")
            clean_non_crypto_sources(table_name, non_crypto, dry_run=False)
        else:
            print("\n🔍 Для выполнения удаления запустите:")
            print("   python analyze_and_clean_sources.py --execute")
    else:
        print("\n✅ Некриптовалютных источников не найдено!")

