"""
Single-command launcher for the Intelligent Route & Delivery Optimization System.
Starts the Flask server which serves both the REST API and the interactive frontend.
"""

import os
import sys
import webbrowser

# Add backend directory to module search path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from app import app

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    URL = f"http://localhost:{PORT}"

    print("=" * 70)
    print("  INTELLIGENT ROUTE & DELIVERY OPTIMIZATION SYSTEM (MUMBAI NETWORK)")
    print("=" * 70)
    print(f"  [>] Server running at: {URL}")
    print(f"  [>] Serving Web UI & API Endpoints")
    print(f"  [>] Press CTRL+C to stop the server")
    print("=" * 70)

    # In non-production local environments, start the server
    app.run(host="0.0.0.0", port=PORT, debug=False)
