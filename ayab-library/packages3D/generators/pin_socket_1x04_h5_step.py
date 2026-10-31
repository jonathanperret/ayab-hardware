"""Write a coloured STEP (AP214) of a low-profile 1x04 2.54 mm female socket, 5.0 mm high
(HC-PM254-5.0H-1x4PZ-02A, LCSC C42163122), as axis-aligned boxes.

Coordinates in mm, footprint frame of Library:PinSocket_1x04_P2.54mm_Vertical_H5.0 with model y = -footprint y
(pin 1 at the origin, pins along footprint +y).

    python3 pin_socket_1x04_h5_step.py ../PinSocket_1x04_P2.54mm_Vertical_H5.0.step"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# same box-to-STEP writer as the OLED model (its file name has dots and it writes on import: take write() only)
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oled_0.91_128x32_step.py')).read()
exec(_src[:_src.index('\ndef oled(')])


def socket(n=4, h=5.0, tail=3.0):
    black, gold, hole = (0.06, 0.06, 0.06), (0.85, 0.7, 0.3), (0.2, 0.2, 0.2)
    fy = lambda y0, y1: (-y1, -y0)    # footprint y (down) -> model y (up)
    b = [(-1.27, 1.27, *fy(-1.27, (n - 1) * 2.54 + 1.27), 0, h, black, 'body')]
    for i in range(n):
        y = i * 2.54
        b.append((-0.32, 0.32, *fy(y - 0.32, y + 0.32), -tail, 0, gold, f'pin{i + 1}'))
        b.append((-0.5, 0.5, *fy(y - 0.5, y + 0.5), h, h + 0.01, hole, f'entry{i + 1}'))
    return b


if __name__ == '__main__':
    write(socket(), sys.argv[1], 'PinSocket_1x04_P2.54mm_Vertical_H5.0')
