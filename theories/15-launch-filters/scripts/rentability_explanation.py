#!/usr/bin/env python3
"""
Profitability Explanation - Detailed Calculations
Explains how to calculate profitability with different winrates and multiples
"""

def calculate_rentability_examples():
    """Calculates and explains profitability with concrete examples"""

    print("💰 PROFITABILITY EXPLANATION")
    print("=" * 60)

    # Example with 1.5x and 56% winrate
    print("\n🎯 EXAMPLE 1: 1.5x multiple with 56% winrate")
    print("-" * 50)

    multiple = 1.5
    winrate = 56  # as a percentage
    loss_rate = 100 - winrate  # 44%

    print(f"📊 Parameters:")
    print(f"   🎯 Multiple: {multiple}x")
    print(f"   ✅ Winrate: {winrate}%")
    print(f"   ❌ Loss rate: {loss_rate}%")

    # Profitability calculation
    # Average gain = (winrate * multiple) - (loss_rate * 1)
    gain_per_trade = (winrate/100 * multiple) - (loss_rate/100 * 1)

    print(f"\n📈 Profitability calculation:")
    print(f"   💰 Average gain per trade = (Winrate × Multiple) - (Loss rate × 1)")
    print(f"   💰 Average gain per trade = ({winrate}% × {multiple}x) - ({loss_rate}% × 1)")
    print(f"   💰 Average gain per trade = {winrate/100 * multiple:.3f} - {loss_rate/100:.3f}")
    print(f"   💰 Average gain per trade = {gain_per_trade:.3f}")

    if gain_per_trade > 0:
        print(f"   ✅ PROFITABLE: +{gain_per_trade:.3f} per trade")
    else:
        print(f"   ❌ NOT PROFITABLE: {gain_per_trade:.3f} per trade")

    # Calculation of the winrate required to be profitable
    required_winrate = 1 / (multiple + 1) * 100
    print(f"\n📋 Winrate required to be profitable:")
    print(f"   📊 Required winrate = 1 / (Multiple + 1) × 100")
    print(f"   📊 Required winrate = 1 / ({multiple} + 1) × 100")
    print(f"   📊 Required winrate = 1 / {multiple + 1} × 100")
    print(f"   📊 Required winrate = {required_winrate:.1f}%")

    # Comparison with different multiples
    print(f"\n📊 COMPARISON WITH DIFFERENT MULTIPLES")
    print("-" * 60)
    print(f"{'Multiple':<8} {'Required Winrate':<15} {'Your Winrate':<15} {'Profitable?'}")
    print("-" * 60)

    multiples_to_test = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    your_winrate = 56

    for mult in multiples_to_test:
        req_winrate = 1 / (mult + 1) * 100
        is_profitable = your_winrate >= req_winrate
        status = "✅ YES" if is_profitable else "❌ NO"
        print(f"{mult:<7.1f}x {req_winrate:<14.1f}% {your_winrate:<14.1f}% {status}")

    # Concrete examples with 100 trades
    print(f"\n🎲 CONCRETE EXAMPLE WITH 100 TRADES")
    print("-" * 50)

    total_trades = 100
    wins = int(total_trades * winrate / 100)
    losses = total_trades - wins

    print(f"📊 Simulation with {total_trades} trades:")
    print(f"   ✅ Wins: {wins} trades")
    print(f"   ❌ Losses: {losses} trades")

    # Calculation of gains and losses
    total_gains = wins * multiple
    total_losses = losses * 1  # Loss of 100% of the invested capital
    net_result = total_gains - total_losses

    print(f"\n💰 Financial results:")
    print(f"   💰 Total gains: {wins} × {multiple}x = {total_gains}")
    print(f"   💰 Total losses: {losses} × 1x = {total_losses}")
    print(f"   💰 Net result: {total_gains} - {total_losses} = {net_result}")

    if net_result > 0:
        print(f"   ✅ PROFIT: +{net_result} units of capital")
        roi = (net_result / total_trades) * 100
        print(f"   📈 Average ROI: +{roi:.2f}% per trade")
    else:
        print(f"   ❌ LOSS: {net_result} units of capital")

    # Explanation of your confusion
    print(f"\n🤔 EXPLANATION OF YOUR CONFUSION")
    print("-" * 50)
    print(f"You thought a 66% winrate was needed for 1.5x.")
    print(f"This calculation would be correct if you lost 100% on every failure.")
    print(f"But in reality, you only lose 100% of your stake (1x).")
    print(f"\n📊 Correct calculation:")
    print(f"   ✅ Gains: {winrate}% × 1.5x = {winrate/100 * 1.5:.3f}")
    print(f"   ❌ Losses: {100-winrate}% × 1x = {(100-winrate)/100:.3f}")
    print(f"   💰 Result: {winrate/100 * 1.5:.3f} - {(100-winrate)/100:.3f} = {gain_per_trade:.3f}")

    # Comparison with different scenarios
    print(f"\n📊 SCENARIO COMPARISON")
    print("-" * 60)
    print(f"{'Multiple':<8} {'Winrate':<8} {'Gain/Trade':<12} {'Profitable?'}")
    print("-" * 60)

    scenarios = [
        (1.5, 56, "Your case"),
        (1.5, 66, "Your estimate"),
        (2.0, 50, "2x case"),
        (3.0, 33, "3x case"),
        (1.5, 40, "Break-even threshold")
    ]

    for mult, wr, description in scenarios:
        gain = (wr/100 * mult) - ((100-wr)/100 * 1)
        status = "✅ YES" if gain > 0 else "❌ NO"
        print(f"{mult:<7.1f}x {wr:<7.1f}% {gain:<11.3f} {status:<10} ({description})")

    # Final recommendation
    print(f"\n🏆 CONCLUSION")
    print("=" * 50)
    print(f"✅ With 1.5x and a 56% winrate, you are PROFITABLE!")
    print(f"📊 Average gain per trade: +{gain_per_trade:.3f}")
    print(f"📈 Average ROI: +{gain_per_trade * 100:.2f}% per trade")
    print(f"💡 Your logic was almost correct, but the calculation")
    print(f"   must account for the fact that you only lose 100% (1x),")
    print(f"   no more, on each failure.")

def main():
    """Main function"""
    calculate_rentability_examples()

    print(f"\n🎯 EXPLANATION COMPLETE!")
    print("=" * 60)
    print(f"💡 Profitability with 1.5x and a 56% winrate is confirmed")

if __name__ == "__main__":
    main()
