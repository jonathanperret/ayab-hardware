"""Datasheet views of the BL-DT in model coordinates (mm): x right, y towards the wheel (= -KiCad footprint y),
z up from the PCB. One scale for the whole drawing page (300 dpi render): PPM = 30.0 px/mm. Anchors (page px):
pegs' centre row 725 = y 1.32 (footprint), body centre column 513 (top view), 1620 (bottom view, mirrored),
512.75 (front elevation)."""
import numpy as np
from PIL import Image
PPM = 30.0
PAGE = __import__('os').path.join(__import__('os').path.dirname(__file__), 'page1-300dpi.png')
page = np.array(Image.open(PAGE).convert('L')) < 128
PEG_ROW, PEG_Y = 725.0, 1.32
def y_of_row(r): return PEG_Y + (PEG_ROW - r) / PPM
def row_of_y(y): return PEG_ROW - (y - PEG_Y) * PPM
VIEWS = {
  # name: (page box, mapping of page px to the view's 2 model axes)
  'top':    dict(box=(270, 420, 760, 880), ax=('x', 'y'), px=lambda c: (c - 513.0) / PPM, py=y_of_row),
  'bottom': dict(box=(1380, 420, 1870, 880), ax=('x', 'y'), px=lambda c: -(c - 1620.0) / PPM, py=y_of_row),
}
