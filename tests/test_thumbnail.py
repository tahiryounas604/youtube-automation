import pytest
from PIL import Image

from youtube_automation.thumbnail import GRADIENTS, make_thumbnail


def test_make_thumbnail_size_and_format(tmp_path):
    out = tmp_path / "thumb.png"
    result = make_thumbnail("How DNS Works", str(out), subtitle="Explained Simply")
    assert result["size"] == (1280, 720)
    img = Image.open(out)
    assert img.size == (1280, 720)
    assert img.format == "PNG"
    # Gradient: top and bottom rows must differ, and image must not be blank.
    assert img.getpixel((640, 5)) != img.getpixel((640, 715))
    assert len(img.getcolors(maxcolors=1_000_000)) > 100


def test_make_thumbnail_gradients_differ(tmp_path):
    outs = {}
    for name in GRADIENTS:
        out = tmp_path / f"{name}.png"
        make_thumbnail("Title", str(out), gradient=name)
        outs[name] = Image.open(out).tobytes()
    assert len(set(outs.values())) == len(GRADIENTS)


def test_make_thumbnail_long_title_wraps_without_error(tmp_path):
    out = tmp_path / "long.png"
    result = make_thumbnail(
        "This Is A Very Long Video Title That Must Wrap Onto Multiple Lines",
        str(out),
    )
    assert Image.open(out).size == (1280, 720)


def test_make_thumbnail_rejects_empty_title(tmp_path):
    with pytest.raises(ValueError):
        make_thumbnail("   ", str(tmp_path / "x.png"))
