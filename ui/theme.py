"""Paletas de color conmutables (oscuro por defecto) y estilos ttk."""

from tkinter import ttk

FONT_FAMILY = "Segoe UI"

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "BG_DARK": "#000000",
        "BG_MEDIUM": "#0A0A0A",
        "BG_LIGHT": "#232323",
        "ACCENT": "#C8C8C8",
        "TEXT_PRIMARY": "#EDEDED",
        "TEXT_SECONDARY": "#8A8A8A",
        "CTRL_BG": "#080808",
        "CTRL_BORDER": "#1F1F1F",
        "TROUGH": "#1A1A1A",
    },
    "light": {
        "BG_DARK": "#F2F2F5",
        "BG_MEDIUM": "#E3E3EA",
        "BG_LIGHT": "#D6DCF5",
        "ACCENT": "#D6395A",
        "TEXT_PRIMARY": "#1B1B2A",
        "TEXT_SECONDARY": "#5C5C70",
        "CTRL_BG": "#FFFFFF",
        "CTRL_BORDER": "#C4C4D0",
        "TROUGH": "#DADAE2",
    },
}

DEFAULT_PALETTE = "dark"
_active = DEFAULT_PALETTE

# Valores iniciales (oscuro); `set_palette` los reemplaza en tiempo de ejecución.
BG_DARK = PALETTES["dark"]["BG_DARK"]
BG_MEDIUM = PALETTES["dark"]["BG_MEDIUM"]
BG_LIGHT = PALETTES["dark"]["BG_LIGHT"]
ACCENT = PALETTES["dark"]["ACCENT"]
TEXT_PRIMARY = PALETTES["dark"]["TEXT_PRIMARY"]
TEXT_SECONDARY = PALETTES["dark"]["TEXT_SECONDARY"]
CTRL_BG = PALETTES["dark"]["CTRL_BG"]
CTRL_BORDER = PALETTES["dark"]["CTRL_BORDER"]
TROUGH = PALETTES["dark"]["TROUGH"]


def set_palette(name: str) -> str:
    """Activa una paleta (``"dark"`` o ``"light"``) y actualiza los colores."""
    global _active
    _active = name if name in PALETTES else DEFAULT_PALETTE
    globals().update(PALETTES[_active])
    return _active


def current_palette() -> str:
    return _active


def toggle() -> str:
    return set_palette("light" if _active == "dark" else "dark")


def setup_styles() -> ttk.Style:
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY,
                    fieldbackground=CTRL_BG, bordercolor=CTRL_BORDER)
    style.configure("TFrame", background=BG_DARK)
    style.configure("TLabelframe", background=BG_DARK, foreground=TEXT_PRIMARY)
    style.configure("TLabelframe.Label", background=BG_DARK, foreground=TEXT_PRIMARY)

    style.configure("TLabel", background=BG_DARK, foreground=TEXT_PRIMARY,
                    font=(FONT_FAMILY, 10))
    style.configure("Title.TLabel", font=(FONT_FAMILY, 16, "bold"))
    style.configure("Subtitle.TLabel", font=(FONT_FAMILY, 10), foreground=TEXT_SECONDARY)
    style.configure("Header.TLabel", font=(FONT_FAMILY, 11, "bold"))
    style.configure("Time.TLabel", font=(FONT_FAMILY, 9), foreground=TEXT_SECONDARY)

    style.configure("TButton", background=CTRL_BG, foreground=TEXT_PRIMARY,
                    borderwidth=1, focusthickness=0, font=(FONT_FAMILY, 10))
    style.map("TButton",
              background=[("active", BG_LIGHT), ("pressed", BG_LIGHT)])

    style.configure("Icon.TButton", background=BG_DARK, borderwidth=0,
                    font=(FONT_FAMILY, 13), padding=(5, 2), width=0)
    style.map("Icon.TButton",
              background=[("active", BG_MEDIUM)])

    style.configure("Active.TButton", background=BG_LIGHT, borderwidth=0,
                    font=(FONT_FAMILY, 13), foreground=ACCENT, padding=(5, 2), width=0)
    style.map("Active.TButton",
              background=[("active", ACCENT), ("pressed", ACCENT)],
              foreground=[("active", BG_DARK)])

    style.configure("Play.TButton", background=BG_DARK, borderwidth=0,
                    font=(FONT_FAMILY, 18), padding=(2, 0), width=3)
    style.map("Play.TButton",
              background=[("active", BG_MEDIUM)])

    style.configure("TEntry", fieldbackground=CTRL_BG, foreground=TEXT_PRIMARY,
                    bordercolor=CTRL_BORDER, insertcolor=TEXT_PRIMARY,
                    lightcolor=CTRL_BORDER, darkcolor=CTRL_BORDER)

    style.configure("TScale", background=BG_DARK, troughcolor=TROUGH,
                    sliderlength=16, slidercolor=TEXT_PRIMARY)
    style.configure("Progress.Horizontal.TScale", background=BG_DARK,
                    troughcolor=TROUGH, sliderlength=14, slidercolor=ACCENT)
    style.configure("Volume.Horizontal.TScale", background=BG_DARK,
                    troughcolor=TROUGH, sliderlength=12, slidercolor=TEXT_PRIMARY)

    style.configure("Vertical.TScrollbar", background=CTRL_BORDER,
                    troughcolor=TROUGH, bordercolor=BG_DARK,
                    arrowcolor=TEXT_PRIMARY, gripcount=0)

    style.configure("Status.TLabel", background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    font=(FONT_FAMILY, 9), padding=(6, 2))
    style.configure("Status.TFrame", background=BG_MEDIUM)

    style.configure("Cover.TFrame", background=CTRL_BG, relief="solid",
                    borderwidth=1)

    return style
