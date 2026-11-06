#!/usr/bin/env python3
"""
Script d'installation automatique des dépendances pour l'optimiseur de filtres
"""

import subprocess
import sys
import os

def install_package(package):
    """Installe un package avec pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🔧 Installation des dépendances pour l'optimiseur de filtres")
    print("=" * 60)
    
    # Liste des packages requis
    packages = [
        "tensorflow>=2.10.0",
        "numpy>=1.21.0", 
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "glob2>=0.7"
    ]
    
    print("📦 Packages à installer:")
    for package in packages:
        print(f"   - {package}")
    
    print("\n🚀 Début de l'installation...")
    
    success_count = 0
    failed_packages = []
    
    for package in packages:
        print(f"\n📥 Installation de {package}...")
        if install_package(package):
            print(f"✅ {package} installé avec succès")
            success_count += 1
        else:
            print(f"❌ Échec de l'installation de {package}")
            failed_packages.append(package)
    
    print("\n" + "=" * 60)
    print("📊 Résumé de l'installation:")
    print(f"✅ Packages installés avec succès: {success_count}/{len(packages)}")
    
    if failed_packages:
        print(f"❌ Packages en échec: {len(failed_packages)}")
        print("Packages qui ont échoué:")
        for package in failed_packages:
            print(f"   - {package}")
        print("\n💡 Suggestions:")
        print("   - Vérifiez votre connexion internet")
        print("   - Mettez à jour pip: python -m pip install --upgrade pip")
        print("   - Essayez d'installer manuellement les packages échoués")
    else:
        print("🎉 Toutes les dépendances ont été installées avec succès!")
        print("\n🚀 Vous pouvez maintenant lancer l'optimiseur:")
        print("   python run_optimizer.py")

if __name__ == "__main__":
    main()


