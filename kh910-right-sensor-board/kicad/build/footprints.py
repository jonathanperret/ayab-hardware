"""footprint choice per reference: KiCad library footprints where one fits, measured custom ones otherwise"""
import math
LIBDIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
CUSTOM = {'VR301', 'PI1', 'PI2', 'CH301'}
def choose(ref, pads):
    """pads: list of (x, y) mm in pin order; returns (library nickname, footprint name)"""
    if ref == 'IC303': return 'Package_DIP', 'DIP-8_W7.62mm'
    if ref.startswith('IC'): return 'Package_DIP', 'DIP-14_W7.62mm'
    if ref == 'J1': return 'Connector_PinHeader_2.54mm', 'PinHeader_1x09_P2.54mm_Vertical'
    if ref == 'J2': return 'Connector_PinHeader_2.54mm', 'PinHeader_1x07_P2.54mm_Vertical'
    if ref.startswith('JP'): return 'kh910', 'SolderJumper_open'
    if ref.startswith('D'): return 'Diode_THT', 'D_DO-35_SOD27_P7.62mm_Horizontal'
    if ref.startswith('R'):
        span = math.dist(pads[0], pads[1])
        return ('Resistor_THT', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal' if span > 7.6 else 'R_Axial_DIN0204_L3.6mm_D1.6mm_P5.08mm_Horizontal')
    return 'kh910', ref
