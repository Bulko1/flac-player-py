"""Utilidades de widgets y formato."""

import tkinter as tk


def format_time(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def attach_tooltip(widget: tk.Misc, text: str):
    """Muestra un tooltip sencillo al pasar el ratón por encima."""
    tip: tk.Toplevel | None = None

    def enter(_event):
        nonlocal tip
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tk.Label(tip, text=text, bg="#333", fg="white",
                 font=("Segoe UI", 9), padx=6, pady=2).pack()

    def leave(_event):
        nonlocal tip
        if tip is not None:
            tip.destroy()
            tip = None

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)
