import os
import sys
from pathlib import Path

# Add project root directory to sys.path so app, config, models, and routes can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Mark that we are in a serverless environment
os.environ.setdefault('VERCEL', '1')

# Import the configured Flask application
from app import app

# Vercel serverless function entrypoint
# The variable name MUST be 'app'
__all__ = ['app']
