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


class VercelPathMiddleware:
    """Ensure Flask correctly receives the original client request path on Vercel."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == '/api/index':
            # Check if original path was passed in headers
            real_path = (
                environ.get('HTTP_X_FORWARDED_URI')
                or environ.get('HTTP_X_MATCHED_PATH')
                or environ.get('RAW_URI')
                or environ.get('REQUEST_URI')
            )
            if real_path and not real_path.startswith('/api/index'):
                environ['PATH_INFO'] = real_path.split('?')[0]
            else:
                environ['PATH_INFO'] = '/'
        elif path.startswith('/api/index/'):
            environ['PATH_INFO'] = path[len('/api/index'):]

        return self.wsgi_app(environ, start_response)


# Wrap with path middleware
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# Expose 'app' for Vercel
__all__ = ['app']
