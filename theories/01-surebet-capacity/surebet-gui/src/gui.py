import tkinter as tk
from tkinter import ttk, messagebox

# Optional ttkbootstrap import for a native dark theme.
try:
    import ttkbootstrap as tb
    from ttkbootstrap import ttk as ttk_bs
    from ttkbootstrap.constants import *  # noqa
    ttk = ttk_bs  # Use bootstrap widgets for all ttk.* calls.
except ImportError:
    tb = None  # Handled below.


def compute_surebet(p1_yes, p1_no, p2_yes, p2_no, bankroll):
    """Return a tuple (message, is_surebet)."""
    # Convert percentages to proportions.
    p1_yes /= 100
    p1_no /= 100
    p2_yes /= 100
    p2_no /= 100

    cost_a = p1_yes + p2_no
    cost_b = p2_yes + p1_no

    if cost_a >= 1 and cost_b >= 1:
        return ("No surebet detected (>= 100%)", False)

    if cost_a < cost_b:
        side_yes = ("platform 1", p1_yes)
        side_no = ("platform 2", p2_no)
        total_cost_pct = cost_a
    else:
        side_yes = ("platform 2", p2_yes)
        side_no = ("platform 1", p1_no)
        total_cost_pct = cost_b

    invest_yes = bankroll * side_yes[1] / total_cost_pct
    invest_no = bankroll * side_no[1] / total_cost_pct
    payout = bankroll / total_cost_pct
    profit = payout - bankroll
    roi = profit / bankroll * 100

    msg = (
        f">>> SUREBET DETECTED! <<<\n\n"
        f"Buy YES on {side_yes[0]} for ${invest_yes:.2f} (price {side_yes[1]*100:.2f}%)\n"
        f"Buy NO  on {side_no[0]} for ${invest_no:.2f} (price {side_no[1]*100:.2f}%)\n\n"
        f"Total cost: ${bankroll:.2f}  •  Guaranteed payout: ${payout:.2f}\n"
        f"Net profit: ${profit:.2f}  •  ROI: {roi:.2f}%"
    )
    return (msg, True)


class SurebetApp(tk.Tk):
    def __init__(self):
        # Initialise the main window with a dark theme when available.
        if tb:
            super().__init__()
            tb.Style("darkly")
        else:
            super().__init__()
            self.configure(bg="#222222")

        # Title / banner.
        title_lbl = ttk.Label(self, text="💹 Binary Surebet Calculator", font=("Segoe UI", 16, "bold"))
        title_lbl.grid(row=0, column=0, columnspan=4, pady=(10, 15))

        padding = {"padx": 5, "pady": 5}

        # Bankroll row.
        ttk.Label(self, text="💰 Bankroll $").grid(row=1, column=0, **padding)
        self.bankroll_var = tk.StringVar(value="100")
        ttk.Entry(self, textvariable=self.bankroll_var, width=12).grid(row=1, column=1, **padding)

        # Separator.
        ttk.Separator(self, orient="horizontal").grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)

        # Platform 1.
        ttk.Label(self, text="🏦 Platform 1 YES %").grid(row=3, column=0, **padding)
        self.p1_yes = tk.StringVar()
        ttk.Entry(self, textvariable=self.p1_yes, width=10).grid(row=3, column=1, **padding)

        ttk.Label(self, text="❌ NO %").grid(row=3, column=2, **padding)
        self.p1_no = tk.StringVar()
        ttk.Entry(self, textvariable=self.p1_no, width=10).grid(row=3, column=3, **padding)

        # Platform 2.
        ttk.Label(self, text="🏦 Platform 2 YES %").grid(row=4, column=0, **padding)
        self.p2_yes = tk.StringVar()
        ttk.Entry(self, textvariable=self.p2_yes, width=10).grid(row=4, column=1, **padding)

        ttk.Label(self, text="❌ NO %").grid(row=4, column=2, **padding)
        self.p2_no = tk.StringVar()
        ttk.Entry(self, textvariable=self.p2_no, width=10).grid(row=4, column=3, **padding)

        # Calculate button.
        btn_style = "success.TButton" if tb else None
        ttk.Button(self, text="🚀 Calculate", style=btn_style, command=self.calculate).grid(row=5, column=0, columnspan=4, pady=(10, 10))

        # Result pane.
        self.result_text = tk.Text(self, height=10, width=65, state="disabled")
        self.result_text.grid(row=6, column=0, columnspan=4, **padding)
        if not tb:
            self.result_text.configure(bg="#1e1e1e", fg="#d7d7d7", insertbackground="#d7d7d7")

    def calculate(self):
        try:
            bankroll = float(self.bankroll_var.get())
            p1_yes = float(self.p1_yes.get())
            p1_no = float(self.p1_no.get())
            p2_yes = float(self.p2_yes.get())
            p2_no = float(self.p2_no.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers.")
            return

        msg, ok = compute_surebet(p1_yes, p1_no, p2_yes, p2_no, bankroll)
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, msg)
        self.result_text.config(state="disabled")
        if not ok:
            messagebox.showinfo("Result", msg)


if __name__ == "__main__":
    app = SurebetApp()
    app.mainloop()
