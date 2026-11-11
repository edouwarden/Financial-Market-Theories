def surebet_binary_two_platforms(total_bankroll=100.0):
    """
    Calculate a surebet between two platforms offering binary YES / NO contracts.

    For each platform, the user enters the YES price then the NO price in percent,
    separated by a space. Example: "60 42" means YES costs 60% and NO costs 42%.

    If "YES price platform A" + "NO price platform B" < 100%, buy YES on A and NO on B.
    Conversely, if "YES price platform B" + "NO price platform A" < 100%, buy YES on B and NO on A.
    In both cases, the algorithm shows how much to invest on each platform to guarantee
    the same payout, and reports the guaranteed profit and ROI.
    """

    def read_prices(platform_idx: int):
        while True:
            raw = input(f"Platform {platform_idx} - YES and NO prices (e.g. 60 40), or q to quit: ")
            if raw.lower() == "q":
                raise SystemExit
            try:
                yes_str, no_str = raw.strip().split()
                yes, no = float(yes_str), float(no_str)
                if not (0 < yes < 100 and 0 < no < 100):
                    print("Both numbers must be between 0 and 100.")
                    continue
                return yes / 100, no / 100  # Convert to proportions.
            except ValueError:
                print("Invalid input. Enter two numbers separated by a space.")

    print("=== Two-platform binary surebet calculator ===")
    p1_yes, p1_no = read_prices(1)
    p2_yes, p2_no = read_prices(2)

    # Test both possible combinations.
    cost_combo_a = p1_yes + p2_no  # Buy YES on platform 1 and NO on platform 2.
    cost_combo_b = p2_yes + p1_no  # Buy YES on platform 2 and NO on platform 1.

    if cost_combo_a >= 1 and cost_combo_b >= 1:
        print("\nNo surebet detected: total cost >= 100% in both directions.")
        return

    if cost_combo_a < cost_combo_b:
        side_yes = ("platform 1", p1_yes)
        side_no = ("platform 2", p2_no)
        total_cost_pct = cost_combo_a
    else:
        side_yes = ("platform 2", p2_yes)
        side_no = ("platform 1", p1_no)
        total_cost_pct = cost_combo_b

    # Allocate proportionally so both outcomes pay the same amount.
    bankroll = total_bankroll
    invest_yes = bankroll * side_yes[1] / total_cost_pct
    invest_no = bankroll * side_no[1] / total_cost_pct
    guaranteed_payout = bankroll / total_cost_pct
    profit = guaranteed_payout - bankroll
    roi = profit / bankroll * 100

    print("\n>>> SUREBET DETECTED! <<<")
    print(f"Buy YES on {side_yes[0]} for ${invest_yes:.2f} (price {side_yes[1]*100:.2f}%)")
    print(f"Buy NO  on {side_no[0]} for ${invest_no:.2f} (price {side_no[1]*100:.2f}%)")
    print(f"\nTotal cost: ${bankroll:.2f}  •  Guaranteed payout: ${guaranteed_payout:.2f}")
    print(f"Net profit: ${profit:.2f}  •  ROI: {roi:.2f}%")


if __name__ == "__main__":
    raw_bankroll = input("Total bankroll to invest (default 100): ")
    try:
        raw_bankroll = float(raw_bankroll)
    except ValueError:
        raw_bankroll = 100.0

    surebet_binary_two_platforms(total_bankroll=raw_bankroll)
