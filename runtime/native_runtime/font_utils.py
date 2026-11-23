from pathlib import Path
from PIL import ImageFont

_FONT = Path(__file__).resolve().parent / 'fonts' / 'DejaVuSansMono.ttf'

def load_font(size):
    return ImageFont.FreeTypeFont(str(_FONT), max(9, int(size)))
