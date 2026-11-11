#!/usr/bin/env python3
"""
Automatic dependency installation script for the filter optimizer
"""

import subprocess
import sys
import os

def install_package(package):
    """Installs a package with pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🔧 Installing dependencies for the filter optimizer")
    print("=" * 60)

    # List of required packages
    packages = [
        "tensorflow>=2.10.0",
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "glob2>=0.7"
    ]

    print("📦 Packages to install:")
    for package in packages:
        print(f"   - {package}")

    print("\n🚀 Starting installation...")

    success_count = 0
    failed_packages = []

    for package in packages:
        print(f"\n📥 Installing {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
            success_count += 1
        else:
            print(f"❌ Failed to install {package}")
            failed_packages.append(package)

    print("\n" + "=" * 60)
    print("📊 Installation summary:")
    print(f"✅ Packages installed successfully: {success_count}/{len(packages)}")

    if failed_packages:
        print(f"❌ Failed packages: {len(failed_packages)}")
        print("Packages that failed:")
        for package in failed_packages:
            print(f"   - {package}")
        print("\n💡 Suggestions:")
        print("   - Check your internet connection")
        print("   - Update pip: python -m pip install --upgrade pip")
        print("   - Try installing the failed packages manually")
    else:
        print("🎉 All dependencies were installed successfully!")
        print("\n🚀 You can now launch the optimizer:")
        print("   python run_optimizer.py")

if __name__ == "__main__":
    main()
