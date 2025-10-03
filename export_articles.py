#!/usr/bin/env python3
"""
Скрипт для экспорта нормализованных данных в JSON
"""
import sys
from pathlib import Path

# Добавляем src в путь для импорта модулей
sys.path.append(str(Path(__file__).parent / 'src'))

from normalization.export_to_json import main

if __name__ == "__main__":
    main()
