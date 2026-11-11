#!/usr/bin/env python3
"""
Launch script for the neural network filter optimizer
"""

import sys
import os

def main():
    print("🚀 Neural Network Filter Optimizer")
    print("=" * 50)
    print("Choose a version:")
    print("1. Basic version (neural_filter_optimizer.py)")
    print("2. Advanced version (advanced_neural_optimizer.py)")
    print("3. Quit")

    while True:
        choice = input("\nYour choice (1-3): ").strip()

        if choice == "1":
            print("\n🔄 Launching the basic version...")
            try:
                from neural_filter_optimizer import main as run_basic
                run_basic()
            except ImportError as e:
                print(f"❌ Error: {e}")
                print("Make sure that neural_filter_optimizer.py exists and that all dependencies are installed.")
            break

        elif choice == "2":
            print("\n🔄 Launching the advanced version...")
            try:
                from advanced_neural_optimizer import main as run_advanced
                run_advanced()
            except ImportError as e:
                print(f"❌ Error: {e}")
                print("Make sure that advanced_neural_optimizer.py exists and that all dependencies are installed.")
            break

        elif choice == "3":
            print("👋 Goodbye!")
            sys.exit(0)

        else:
            print("❌ Invalid choice. Please enter 1, 2 or 3.")

if __name__ == "__main__":
    main()
