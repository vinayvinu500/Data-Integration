import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the FastAPI app
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)