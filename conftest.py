# conftest.py
import sys
from pathlib import Path

# Add project root to sys.path so modules like `api`, `graph`, `config` resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))