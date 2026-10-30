# BL-DT model vs datasheet overlay

Draws `ayab-library/packages3D/SW-SMD_BL-DT.step` (built by `packages3D/generators/sw_smd_bl_dt_step.py`,
CadQuery) over the drawing page of the SHOU HAN BL-DT datasheet (LCSC C53223909, `BL-DT_datasheet_C53223909.pdf`):

    pdftoppm -r 300 -f 1 -l 1 -png BL-DT_datasheet_C53223909.pdf page && mv page-1.png page1-300dpi.png
    python3 ov.py ../../packages3D/SW-SMD_BL-DT.step overlay.png

All views of the drawing share one scale: 30.0 px/mm on the 300 dpi render (12.34, 11.90, 2.16, 6.65, 1.10, 3.40,
5.00, 2.50, 10.80, 1.00, 3.65, 1.65 agree within 0.05 mm; only the ring is drawn 14.6 wide for a 14.20
dimension). `views.py` holds that scale and the anchors: the pegs (y 1.32) on page row 725, the body's centre
column in the top (513), bottom (1620, mirrored) and front (512.75) views, z 0 on row 1432 (front) and column
1118.5 (side). The model is blended over each view; drawing lines it covers turn red, lines left black are
outside it. Needs cadquery, numpy, pillow, poppler-utils.
