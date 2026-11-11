#!/usr/bin/env python3
"""
Test script to verify that the optimization system works correctly
"""

import os
import json
import glob
import sys

def test_dependencies():
    """Tests whether all dependencies are installed"""
    print("🔍 Testing dependencies...")

    required_packages = [
        'tensorflow', 'numpy', 'pandas', 'sklearn',
        'matplotlib', 'seaborn', 'glob'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Run: python install_dependencies.py")
        return False

    print("✅ All dependencies are installed")
    return True

def test_data_files():
    """Tests whether the data files exist"""
    print("\n📁 Testing data files...")

    # Check the historical data
    historical_files = glob.glob('data/new_*.csv')
    if historical_files:
        print(f"✅ Historical data found: {len(historical_files)} files")
    else:
        print("❌ No historical data files found (data/new_*.csv)")
        return False

    # Check the success data
    success_files = glob.glob('data/success_*.csv')
    if success_files:
        print(f"✅ Success data found: {len(success_files)} files")
    else:
        print("❌ No success data files found (data/success_*.csv)")
        return False

    return True

def test_data_loading():
    """Tests data loading"""
    print("\n📥 Testing data loading...")

    try:
        # Test with a small sample
        from neural_filter_optimizer import NeuralFilterOptimizer

        optimizer = NeuralFilterOptimizer()
        optimizer.load_data()

        if len(optimizer.historical_data) > 0:
            print(f"✅ Historical data loaded: {len(optimizer.historical_data)} tokens")
        else:
            print("❌ No historical data loaded")
            return False

        if len(optimizer.success_data) > 0:
            print(f"✅ Success data loaded: {len(optimizer.success_data)} records")
        else:
            print("❌ No success data loaded")
            return False

        return True

    except Exception as e:
        print(f"❌ Error during loading: {e}")
        return False

def test_model_creation():
    """Tests the creation of a simple model"""
    print("\n🧠 Testing model creation...")

    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        # Create a simple model
        model = keras.Sequential([
            layers.Dense(64, activation='relu', input_shape=(13,)),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])

        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

        print("✅ Model created successfully")
        return True

    except Exception as e:
        print(f"❌ Error during model creation: {e}")
        return False

def test_advanced_optimizer():
    """Tests the advanced optimizer"""
    print("\n🚀 Testing the advanced optimizer...")

    try:
        from advanced_neural_optimizer import AdvancedNeuralFilterOptimizer

        optimizer = AdvancedNeuralFilterOptimizer()
        print("✅ Advanced optimizer imported successfully")
        return True

    except Exception as e:
        print(f"❌ Error with the advanced optimizer: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing the filter optimization system")
    print("=" * 50)

    tests = [
        ("Dependencies", test_dependencies),
        ("Data files", test_data_files),
        ("Data loading", test_data_loading),
        ("Model creation", test_model_creation),
        ("Advanced optimizer", test_advanced_optimizer)
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed_tests += 1
            else:
                print(f"❌ Test '{test_name}' failed")
        except Exception as e:
            print(f"❌ Test '{test_name}' raised an error: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test summary: {passed_tests}/{total_tests} passed")

    if passed_tests == total_tests:
        print("🎉 All tests passed! The system is ready.")
        print("\n🚀 You can now launch the optimizer:")
        print("   python run_optimizer.py")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        print("\n💡 Possible solutions:")
        print("   - Run: python install_dependencies.py")
        print("   - Check that your data is in the 'data/' folder")
        print("   - Check the Python version (3.8+)")

if __name__ == "__main__":
    main()
