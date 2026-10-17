"""Pruebas de layout: orden vertical y ausencia de recortes."""

import tkinter as tk
from tkinter import ttk

import pytest


@pytest.fixture
def app(monkeypatch):
    # Evita leer/escribir el estado real del usuario.
    monkeypatch.setattr("storage.load_state", lambda: {})
    monkeypatch.setattr("storage.save_state", lambda data: None)

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Sin entorno gráfico disponible")

    from ui.app import FlacPlayerUI

    ui = FlacPlayerUI(root)
    root.update_idletasks()
    root.update()
    yield root, ui
    try:
        root.destroy()
    except tk.TclError:
        pass


def _assert_children_fit(widget, path=""):
    width = widget.winfo_width()
    height = widget.winfo_height()
    for child in widget.winfo_children():
        if not child.winfo_ismapped():
            continue
        name = f"{path}{child.winfo_class()}"
        right = child.winfo_x() + child.winfo_width()
        bottom = child.winfo_y() + child.winfo_height()
        assert right <= width + 1, f"{name} desborda a la derecha ({right} > {width})"
        assert bottom <= height + 1, f"{name} desborda abajo ({bottom} > {height})"
        _assert_children_fit(child, f"{name}/")


def _iter_widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from _iter_widgets(child)


def _buttons(root):
    return [w for w in _iter_widgets(root) if isinstance(w, ttk.Button)]


def test_icon_buttons_use_natural_width(app):
    """Los botones de icono no deben fijar un ancho en caracteres (recorta emoji)."""
    style = ttk.Style()
    for name in ("Icon.TButton", "Active.TButton"):
        assert int(style.lookup(name, "width") or 0) <= 0, (
            f"el estilo {name} fija un width que recorta los glifos")

    root, _ = app
    for btn in _buttons(root):
        if btn.cget("style") in ("Icon.TButton", "Active.TButton"):
            assert int(btn.cget("width") or 0) <= 0, (
                f"botón de icono {btn.cget('text')!r} usa width fijo (recorta el glifo)")


def test_buttons_not_compressed_below_natural(app):
    root, _ = app
    for btn in _buttons(root):
        assert btn.winfo_width() >= btn.winfo_reqwidth() - 1


def test_no_horizontal_clipping(app):
    root, _ = app
    assert root.winfo_reqwidth() <= root.winfo_width()


def test_panels_fit_inside_window(app):
    root, ui = app
    width = root.winfo_width()
    for panel in (ui.playlist_panel, ui.transport_panel, ui.track_panel):
        assert panel.winfo_x() + panel.winfo_width() <= width + 1
        _assert_children_fit(panel, f"{panel.winfo_class()}/")


def test_vertical_order(app):
    _, ui = app
    assert ui.playlist_panel.winfo_y() < ui.transport_panel.winfo_y()
    assert ui.transport_panel.winfo_y() < ui.track_panel.winfo_y()


def test_minimum_size_covers_content(app):
    root, _ = app
    min_w, min_h = root.minsize()
    assert min_w >= root.winfo_reqwidth()
    assert min_h >= root.winfo_reqheight()


def test_transport_and_volume_visible_at_min_size(app):
    root, ui = app
    root.geometry(f"{root.minsize()[0]}x{root.minsize()[1]}")
    root.update_idletasks()
    root.update()

    width = root.winfo_width()
    controls = ui.transport_panel.winfo_children()[-1]  # fila de transporte
    for child in controls.winfo_children():
        assert child.winfo_x() + child.winfo_width() <= width + 1


def test_theme_toggle_changes_colors(app):
    from ui import theme

    root, ui = app
    ui._apply_theme("dark")
    root.update_idletasks()
    dark_bg = root.cget("bg")

    ui._cmd_toggle_theme()
    root.update_idletasks()
    assert theme.current_palette() == "light"
    assert root.cget("bg") != dark_bg

    ui._cmd_toggle_theme()
    root.update_idletasks()
    assert theme.current_palette() == "dark"
    assert root.cget("bg") == dark_bg
