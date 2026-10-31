"""Fast, basic renders with OpenSCAD's OpenGL preview (no ray tracing).

Usage: python3 quick_render.py WORKDIR OUTDIR [--iso] [--anim]
  --iso: only the isometric view (01_assembled); --anim: also the animations
WORKDIR holds tray_asm.stl, lid_asm.stl, pcb_only.stl and comp/<REF>.stl (see README).
Needs openscad and xvfb-run; ffmpeg for the animations.
Frame: X = KiCad x, Y = -KiCad y, Z = 0 at the PCB bottom (same as the .scad)."""
import glob, os, subprocess, sys, tempfile
import numpy as np
from stlio import load_stl, save_stl

W, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)
CTR = (132.25, -66.55, 8)
SIZE = (1200, 900)

# one STL for all the components (OpenSCAD imports one file much faster than 60)
comps = W + '/components.stl'
save_stl(comps, np.concatenate([load_stl(f) for f in sorted(glob.glob(W + '/comp/*.stl'))]))

def scene(tray=True, lid=True, board=True, lid_z=0, board_z=0, lid_alpha=1.0):
    s = []
    if tray:
        s.append('color("DimGray") import("%s/tray_asm.stl");' % W)
    if board:
        s.append('translate([0,0,%g]) { color("SeaGreen") import("%s/pcb_only.stl"); color("Gainsboro") import("%s"); }' % (board_z, W, comps))
    if lid:
        s.append('translate([0,0,%g]) color("WhiteSmoke", %g) import("%s/lid_asm.stl");' % (lid_z, lid_alpha, W))
    return '\n'.join(s) + '\n'

def openscad(src, out, extra):
    with tempfile.NamedTemporaryFile('w', suffix='.scad', delete=False) as f:
        f.write(src)
    cmd = ['xvfb-run', '-a', '-s', '-screen 0 1600x1200x24', 'openscad', '--preview',
           '--imgsize=%d,%d' % SIZE, '--colorscheme=Tomorrow', '-o', out] + extra + [f.name]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(f.name)

def cam(rx, rz, d=None, ctr=CTR):
    # --camera=translate_x,y,z,rot_x,y,z,dist; without d, OpenSCAD frames the whole scene
    c = ['--camera=%g,%g,%g,%g,0,%g,%g' % (ctr[0], ctr[1], ctr[2], rx, rz, d or 200)]
    return c if d else c + ['--viewall', '--autocenter']

STILLS = {
    '01_assembled':         (scene(), cam(55, 330)),
    '02_assembled_right':   (scene(), cam(60, 60)),
    '03_xray':              (scene(lid_alpha=0.35), cam(45, 330)),
    '04_exploded':          (scene(board_z=18, lid_z=45), cam(62, 330)),
    '05_tray_with_board':   (scene(lid=False), cam(40, 340)),
    '06_tray':              (scene(lid=False, board=False), cam(40, 340)),
    '07_lid_top':           (scene(tray=False, board=False), cam(35, 340)),
    '08_lid_underside':     (scene(tray=False, board=False), cam(145, 340)),
    '09_openings_usb':      (scene(), ['--projection=o'] + cam(90, 0)),
    '10_openings_din_wheel': (scene(), ['--projection=o'] + cam(90, 90)),
}
if '--iso' in sys.argv:
    STILLS = {'01_assembled': STILLS['01_assembled']}
for name, (src, extra) in STILLS.items():
    openscad(src, '%s/%s.png' % (OUT, name), extra)
    print(name, flush=True)

# animations: one OpenSCAD run per frame (2021.01 has no --animate on the command line,
# and ignores -D $t: the frame time is passed as tt)
def animate(name, src, frames, fps, camera):
    d = tempfile.mkdtemp()
    for i in range(frames):
        t = i / frames
        openscad(src, '%s/f%05d.png' % (d, i), ['-D', 'tt=%g' % t] + camera(t))
    pat = d + '/f%05d.png'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', pat,
                    '-vf', 'scale=800:-2', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '22',
                    '-movflags', '+faststart', '%s/%s.mp4' % (OUT, name)], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', pat,
                    '-vf', 'scale=560:-2,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse',
                    '%s/%s.gif' % (OUT, name)], check=True)
    for f in glob.glob(d + '/*'):
        os.unlink(f)
    os.rmdir(d)
    print(name, flush=True)

if '--anim' not in sys.argv:
    sys.exit(0)
animate('turntable', scene(), 48, 16, lambda t: cam(60, 360 * t, 260))
# exploded: open, hold, close
src = ('tt = 0;\nk = tt < 0.4 ? tt / 0.4 : (tt < 0.6 ? 1 : (1 - tt) / 0.4);\n'
       + scene().replace('translate([0,0,0]) { color("SeaGreen")', 'translate([0,0,18 * k]) { color("SeaGreen")')
                .replace('translate([0,0,0]) color("WhiteSmoke"', 'translate([0,0,45 * k]) color("WhiteSmoke"'))
animate('exploded', src, 50, 16, lambda t: cam(62, 330, 320, (132.25, -66.55, 22)))
