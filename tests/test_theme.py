import pytest

from ui import theme


@pytest.fixture(autouse=True)
def reset_theme():
    theme.set_palette(theme.DEFAULT_PALETTE)
    yield
    theme.set_palette(theme.DEFAULT_PALETTE)


def test_palettes_share_the_same_keys():
    assert set(theme.PALETTES["dark"]) == set(theme.PALETTES["light"])


def test_default_is_dark():
    assert theme.DEFAULT_PALETTE == "dark"


def test_set_palette_updates_module_colors():
    theme.set_palette("light")
    assert theme.current_palette() == "light"
    assert theme.BG_DARK == theme.PALETTES["light"]["BG_DARK"]
    assert theme.TEXT_PRIMARY == theme.PALETTES["light"]["TEXT_PRIMARY"]


def test_toggle_switches_back_and_forth():
    theme.set_palette("dark")
    assert theme.toggle() == "light"
    assert theme.toggle() == "dark"


def test_unknown_palette_falls_back_to_default():
    assert theme.set_palette("does-not-exist") == theme.DEFAULT_PALETTE


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    value = hexcolor.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def test_dark_palette_is_grayscale():
    for name, value in theme.PALETTES["dark"].items():
        red, green, blue = _rgb(value)
        assert red == green == blue, f"{name}={value} no es un gris"


def test_dark_root_is_almost_black():
    red, green, blue = _rgb(theme.PALETTES["dark"]["BG_DARK"])
    assert max(red, green, blue) <= 8
