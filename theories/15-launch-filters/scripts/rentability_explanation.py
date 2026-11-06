#!/usr/bin/env python3
"""
Explication de la Rentabilité - Calculs Détaillés
Explique comment calculer la rentabilité avec différents winrates et multiples
"""

def calculate_rentability_examples():
    """Calcule et explique la rentabilité avec des exemples concrets"""
    
    print("💰 EXPLICATION DE LA RENTABILITÉ")
    print("=" * 60)
    
    # Exemple avec 1.5x et 56% de winrate
    print("\n🎯 EXEMPLE 1: Multiple 1.5x avec 56% de winrate")
    print("-" * 50)
    
    multiple = 1.5
    winrate = 56  # en pourcentage
    loss_rate = 100 - winrate  # 44%
    
    print(f"📊 Paramètres:")
    print(f"   🎯 Multiple: {multiple}x")
    print(f"   ✅ Winrate: {winrate}%")
    print(f"   ❌ Taux de perte: {loss_rate}%")
    
    # Calcul de rentabilité
    # Gain moyen = (winrate * multiple) - (loss_rate * 1)
    gain_per_trade = (winrate/100 * multiple) - (loss_rate/100 * 1)
    
    print(f"\n📈 Calcul de rentabilité:")
    print(f"   💰 Gain moyen par trade = (Winrate × Multiple) - (Taux de perte × 1)")
    print(f"   💰 Gain moyen par trade = ({winrate}% × {multiple}x) - ({loss_rate}% × 1)")
    print(f"   💰 Gain moyen par trade = {winrate/100 * multiple:.3f} - {loss_rate/100:.3f}")
    print(f"   💰 Gain moyen par trade = {gain_per_trade:.3f}")
    
    if gain_per_trade > 0:
        print(f"   ✅ RENTABLE: +{gain_per_trade:.3f} par trade")
    else:
        print(f"   ❌ NON RENTABLE: {gain_per_trade:.3f} par trade")
    
    # Calcul du winrate requis pour être rentable
    required_winrate = 1 / (multiple + 1) * 100
    print(f"\n📋 Winrate requis pour être rentable:")
    print(f"   📊 Winrate requis = 1 / (Multiple + 1) × 100")
    print(f"   📊 Winrate requis = 1 / ({multiple} + 1) × 100")
    print(f"   📊 Winrate requis = 1 / {multiple + 1} × 100")
    print(f"   📊 Winrate requis = {required_winrate:.1f}%")
    
    # Comparaison avec différents multiples
    print(f"\n📊 COMPARAISON AVEC DIFFÉRENTS MULTIPLES")
    print("-" * 60)
    print(f"{'Multiple':<8} {'Winrate Requis':<15} {'Votre Winrate':<15} {'Rentable?'}")
    print("-" * 60)
    
    multiples_to_test = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    your_winrate = 56
    
    for mult in multiples_to_test:
        req_winrate = 1 / (mult + 1) * 100
        is_profitable = your_winrate >= req_winrate
        status = "✅ OUI" if is_profitable else "❌ NON"
        print(f"{mult:<7.1f}x {req_winrate:<14.1f}% {your_winrate:<14.1f}% {status}")
    
    # Exemples concrets avec 100 trades
    print(f"\n🎲 EXEMPLE CONCRET AVEC 100 TRADES")
    print("-" * 50)
    
    total_trades = 100
    wins = int(total_trades * winrate / 100)
    losses = total_trades - wins
    
    print(f"📊 Simulation avec {total_trades} trades:")
    print(f"   ✅ Wins: {wins} trades")
    print(f"   ❌ Pertes: {losses} trades")
    
    # Calcul des gains et pertes
    total_gains = wins * multiple
    total_losses = losses * 1  # Perte de 100% du capital investi
    net_result = total_gains - total_losses
    
    print(f"\n💰 Résultats financiers:")
    print(f"   💰 Gains totaux: {wins} × {multiple}x = {total_gains}")
    print(f"   💰 Pertes totales: {losses} × 1x = {total_losses}")
    print(f"   💰 Résultat net: {total_gains} - {total_losses} = {net_result}")
    
    if net_result > 0:
        print(f"   ✅ PROFIT: +{net_result} unités de capital")
        roi = (net_result / total_trades) * 100
        print(f"   📈 ROI moyen: +{roi:.2f}% par trade")
    else:
        print(f"   ❌ PERTE: {net_result} unités de capital")
    
    # Explication de votre confusion
    print(f"\n🤔 EXPLICATION DE VOTRE CONFUSION")
    print("-" * 50)
    print(f"Vous pensiez qu'il fallait 66% de winrate pour 1.5x.")
    print(f"Ce calcul serait correct si vous perdiez 100% à chaque échec.")
    print(f"Mais en réalité, vous ne perdez que 100% de votre mise (1x).")
    print(f"\n📊 Calcul correct:")
    print(f"   ✅ Gains: {winrate}% × 1.5x = {winrate/100 * 1.5:.3f}")
    print(f"   ❌ Pertes: {100-winrate}% × 1x = {(100-winrate)/100:.3f}")
    print(f"   💰 Résultat: {winrate/100 * 1.5:.3f} - {(100-winrate)/100:.3f} = {gain_per_trade:.3f}")
    
    # Comparaison avec différents scénarios
    print(f"\n📊 COMPARAISON DE SCÉNARIOS")
    print("-" * 60)
    print(f"{'Multiple':<8} {'Winrate':<8} {'Gain/Trade':<12} {'Rentable?'}")
    print("-" * 60)
    
    scenarios = [
        (1.5, 56, "Votre cas"),
        (1.5, 66, "Votre estimation"),
        (2.0, 50, "Cas 2x"),
        (3.0, 33, "Cas 3x"),
        (1.5, 40, "Seuil de rentabilité")
    ]
    
    for mult, wr, description in scenarios:
        gain = (wr/100 * mult) - ((100-wr)/100 * 1)
        status = "✅ OUI" if gain > 0 else "❌ NON"
        print(f"{mult:<7.1f}x {wr:<7.1f}% {gain:<11.3f} {status:<10} ({description})")
    
    # Recommandation finale
    print(f"\n🏆 CONCLUSION")
    print("=" * 50)
    print(f"✅ Avec 1.5x et 56% de winrate, vous êtes RENTABLE!")
    print(f"📊 Gain moyen par trade: +{gain_per_trade:.3f}")
    print(f"📈 ROI moyen: +{gain_per_trade * 100:.2f}% par trade")
    print(f"💡 Votre logique était presque correcte, mais le calcul")
    print(f"   doit tenir compte que vous ne perdez que 100% (1x),")
    print(f"   pas plus, à chaque échec.")

def main():
    """Fonction principale"""
    calculate_rentability_examples()
    
    print(f"\n🎯 EXPLICATION TERMINÉE!")
    print("=" * 60)
    print(f"💡 La rentabilité avec 1.5x et 56% de winrate est confirmée")

if __name__ == "__main__":
    main()




