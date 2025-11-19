#!/usr/bin/env python3
"""
Quick launcher for AgentManager Dashboard
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import and run dashboard
from dashboard import main

if __name__ == "__main__":
    print("🚀 Starting AgentManager Dashboard...")
    print("📊 Connecting to server at http://localhost:8001")
    print("⏱️  Refresh intervals:")
    print("   - Workers: 2 seconds")
    print("   - Workflows: 3 seconds")
    print("   - Metrics: 5 seconds")
    print("\n✨ Dashboard loading...\n")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard closed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
