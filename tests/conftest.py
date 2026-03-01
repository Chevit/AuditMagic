import sys
import os

# Allow test files to import from src/ without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
