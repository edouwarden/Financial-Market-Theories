#!/usr/bin/env python3
"""
Script de lancement pour l'optimiseur de filtres par réseau neuronal
"""

import sys
import os

def main():
    print("🚀 Optimiseur de Filtres par Réseau Neuronal")
    print("=" * 50)
    print("Choisissez une version:")
    print("1. Version de base (neural_filter_optimizer.py)")
    print("2. Version avancée (advanced_neural_optimizer.py)")
    print("3. Quitter")
    
    while True:
        choice = input("\nVotre choix (1-3): ").strip()
        
        if choice == "1":
            print("\n🔄 Lancement de la version de base...")
            try:
                from neural_filter_optimizer import main as run_basic
                run_basic()
            except ImportError as e:
                print(f"❌ Erreur: {e}")
                print("Assurez-vous que neural_filter_optimizer.py existe et que toutes les dépendances sont installées.")
            break
            
        elif choice == "2":
            print("\n🔄 Lancement de la version avancée...")
            try:
                from advanced_neural_optimizer import main as run_advanced
                run_advanced()
            except ImportError as e:
                print(f"❌ Erreur: {e}")
                print("Assurez-vous que advanced_neural_optimizer.py existe et que toutes les dépendances sont installées.")
            break
            
        elif choice == "3":
            print("👋 Au revoir!")
            sys.exit(0)
            
        else:
            print("❌ Choix invalide. Veuillez entrer 1, 2 ou 3.")

if __name__ == "__main__":
    main()

