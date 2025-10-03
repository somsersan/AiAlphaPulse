#!/usr/bin/env python3
"""
Скрипт для обработки и нормализации новостных статей
"""
import sys
from pathlib import Path

# Добавляем src в путь для импорта модулей
sys.path.append(str(Path(__file__).parent / 'src'))

from normalization.process_articles import main

if __name__ == "__main__":
    main()
