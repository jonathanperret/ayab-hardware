// =====================================================================
//  AYAB Silver Reed ESP32 board (ayab-sr-esp32) - 3D printed enclosure
// =====================================================================
//  Two parts:
//    * tray : bottom part. The PCB sits on 3 standoffs (H1, H2, H3). Holds the
//             USB-C openings (J1 power/PD, J2 ESP32), the lower half of the
//             DIN-7 opening (J3) and the thumb-wheel slot (S1).
//    * lid  : top part. A flat cover just above the OLED (the tallest
//             part besides J3), with a hump over the DIN-7 socket J3 that
//             also carries the upper part of the DIN opening. OLED window
//             (U5), tab closing the S1
//             slot from above, and 3 columns that clamp the PCB and receive
//             the screws (M3 heat-set inserts by default).
//             J4 and J14 are not populated (DNP) and get no opening.
//
//  Closure: 3 x M3x12 countersunk screws (ISO 10642 / DIN 7991) inserted
//  from UNDER the tray, through the tray standoff and the PCB mounting
//  hole, into an M3 heat-set insert at the bottom of each lid column.
//  The PCB is clamped between the standoff and the lid column.
//
//  Coordinate system: X = KiCad x, Y = -KiCad y (so the model is not
//  mirrored), Z = 0 at the PCB bottom face. All board positions below are
//  copied from ayab-sr-esp32.kicad_pcb (commit d8073cd, before the board was
//  turned 90 deg) and can be typed in those KiCad coordinates thanks to the
//  kp() helper. The board has since been lengthened by 6 mm on the USB-C /
//  mounting-hole end (old x - 6: bx0, holes, usb_x); J3, U5 and S1 did not move.
//  The OLED U5 now plugs into a 5.0 mm socket J15 (glass 5 mm higher, lid
//  raised to match) and its far end rests on a tray post through the PCB.
//
//  Usage:
//    openscad -D 'part="tray_print"' -o bottom.stl ayab-sr-esp32-enclosure.scad
//    openscad -D 'part="lid_print"'  -o lid.stl    ayab-sr-esp32-enclosure.scad
//  part = "assembly" | "exploded" | "tray" | "lid" | "tray_print" | "lid_print"
// =====================================================================

part = "assembly";

/* [General] */
wall        = 2.0;    // side wall thickness
floor_t     = 2.0;    // tray floor thickness
top_t       = 2.0;    // lid top thickness
clr         = 0.3;    // clearance PCB edge -> wall inner face
clr_bottom  = 0.5;    // clearance on the USB/antenna edge (ESP32 antenna overhangs the edge by 0.16 mm)
standoff_h  = 4.0;    // gap PCB bottom -> floor top (THT pins go down to -2.0 mm)
standoff_d  = 7.0;
pcb_t       = 1.6;
split_z     = 7.8;    // height (from PCB bottom) of the tray / lid joint (= lid ceiling)
joint_gap   = 0.15;   // tray wall is shorter by this: the PCB clamp, not the walls, takes the load
oled_socket_h = 5.0;  // J15 low-profile socket (HC-PM254-5.0H-1x4PZ-02A) under the module's 2.5 mm pin spacer
oled_top    = 6.74 + oled_socket_h;    // top of the OLED glass (U5), tallest part besides J3 (11.74)
oled_bottom = pcb_t + oled_socket_h + 2.5;  // underside of the OLED module PCB (9.1)
ceiling_z   = oled_top + 1.06;         // lid inner ceiling (12.8)
top_z       = ceiling_z + top_t;       // outside top of the lid (14.8)
din_top     = 21.25;  // top of the DIN socket J3, from the STEP export
hump_ceiling_z = din_top + 1.05;       // inner ceiling of the DIN hump (22.3)
hump_top_z  = hump_ceiling_z + top_t;  // outside top of the hump (24.3)
hump_cav    = [162.0, 0, 181.9, 46.6];   // hump cavity (KiCad x0,y0,x1,y1), up to the wall in front of the DIN (din_face_x + 0.2); J3 spans x 162.6..181.7, y 24.9..46.2
bottom_z    = -standoff_h - floor_t;   // outside bottom of the tray (-6.0)

/* [Screws / inserts] */
use_inserts   = true;   // true: M3 heat-set inserts in the lid columns; false: self-tapping into plastic
insert_d      = 4.0;    // hole for a standard M3 heat-set insert (OD 4.6-5.0, L 5.7)
selftap_d     = 2.5;    // hole for a M3 thread-forming screw directly in the plastic
insert_hole_l = 6.5;    // hole depth in the column (insert + room for the screw tip; M3x12 screw tip at 6.0)
column_d      = 6.6;    // lid column OD (PCB pad 6 mm; 0.4 mm from the OLED module at H2)
screw_clear_d = 3.4;    // M3 clearance hole through the standoff
csk_d         = 6.4;    // countersink diameter at the tray bottom (M3 countersunk head = 6.0)

/* [Lid options] */
lid_text      = "AYAB  Silver Reed";
engrave       = 0.5;    // depth of engraved text
lip_h         = 2.0;    // alignment lip under the lid, entering the tray
lip_t         = 1.2;
lip_clr       = 0.2;

$fn = 48;

// ---------------------------------------------------------------------
// Board data (KiCad coordinates, mm)
// ---------------------------------------------------------------------
function kp(x, y) = [x, -y];

bx0 = 100.9; bx1 = 190.0; by0 = 24.1; by1 = 88.6;   // Edge.Cuts bounding box
notch_x = 181.3;  notch_y = 48.0;                    // top-right notch (DIN socket)

holes = [[106.175, 29.475], [167.0, 57.4], [118.5, 64.8]]; // H1, H2, H3

// USB-C receptacles (front of shell at y=88.3, shell 8.94 x 3.16 mm, centre z=3.33)
usb_x   = [107.98, 122.78];     // J1 (power / USB-PD), J2 (ESP32 USB): 14.8 mm apart, like the ports of a MacBook
usb_lbl = ["PWR", "ESP32"];
usb_zc  = 3.33;
usb_w   = 9.6;  usb_h = 3.9;  usb_r = 1.4;         // through opening
usbp_w  = 13.0; usbp_h = 7.6; usbp_r = 2.0;        // outer pocket for the cable overmold (one per plug,
                                                   // merged into a single pocket since the plugs are only 14.8 mm apart)
usbp_depth = 1.2;

// DIN-7 socket J3: axis along +x, centre found by fitting the socket ring of the STEP model
din_y = 35.46;  din_zc = 11.62;
din_face_x = 181.7;           // front face of the metal shell
din_clear_y = 48.01;          // nothing of the case at x > din_face_x for KiCad y < din_clear_y (PCB notch edge 48.0):
                              // the front of the socket is fully clear, the case ends flush with its face
oled_skirt_t = 0.45;          // lid skirt closing the OLED compartment along the notch edge, above the PCB

// Thumb-wheel S1 (SHOU HAN BL-DT): wheel protrudes to x=193.7, y 60.85..75.75, z 1.6..3.6 (4.0 body)
s1_y0 = 60.85; s1_y1 = 75.75;   // wheel extent along y (with the wall clearance below)
s1_slot_clr = 0.8;
s1_slot_z0  = 1.0;            // bottom of the slot
s1_tab_z0   = 4.6;            // bottom of the lid tab closing the slot from above
thumb_y0 = 57.15; thumb_y1 = 79.45; thumb_depth = 1.0;   // outer recess for the thumb

// OLED U5 (HS91L02W2C01): glass top at z=6.74 (oled_top), active area x 181.0..186.6, y 57.62..80.0
win_x0 = 180.25; win_x1 = 187.35; win_y0 = 56.87; win_y1 = 80.77; // window = active area + 0.75, 45 deg chamfer outwards

// Support post under the far end of the OLED module (the end away from its pins), standing on the
// tray floor and going up through a 3.6 mm hole in the PCB (board KiCad 161.0, 32.3 today)
oled_post   = [182.7, 85.1];   // centre
oled_post_d = 3.0;
oled_post_gap = 0.1;           // below the module underside, so the post supports it without lifting it



// ---------------------------------------------------------------------
// 2D helpers
// ---------------------------------------------------------------------
// rounded rectangle from KiCad corner coordinates
module krect(x0, y0, x1, y1, r = 0.01) {
    translate([x0 + r, -y1 + r]) offset(r = r) square([x1 - x0 - 2 * r, y1 - y0 - 2 * r]);
}
module rrect_c(w, h, r) {   // centred rounded rectangle
    offset(r = r) square([w - 2 * r, h - 2 * r], center = true);
}

// inner face of the walls
module cavity2d() {
    union() {
        // left part, up to the DIN notch (x = 181.9: 0.2 mm in front of the DIN shell face)
        krect(bx0 - clr, by0 - clr, din_face_x + 0.2, by1 + clr_bottom, 2.0 + clr);
        // right part under the notch (OLED / thumb-wheel)
        krect(150, notch_y - clr, bx1 + clr, by1 + clr_bottom, 0.5);
    }
}
module outer2d() { offset(r = wall) cavity2d(); }

// ---------------------------------------------------------------------
// Cutters shared by both parts
// ---------------------------------------------------------------------
module din_clear() {   // everything in front of the socket face goes, the case ends flush with it
    translate([din_face_x, -din_clear_y, bottom_z - 1]) cube([30, 60, 50]);
    translate([din_face_x, -100, top_z + 0.01]) cube([30, 200, 50]);   // the hump ends flush with the face too
}

// the OLED compartment loses its wall towards the DIN: close it along the notch edge instead
module tray_notch_closer() {   // under the PCB, from the floor to just below the board
    translate([din_face_x, -(din_clear_y + wall), -standoff_h - 0.01])
        cube([bx1 + clr + wall - din_face_x, wall, standoff_h - 0.2 + 0.01]);
}
module lid_notch_skirt() {     // thin skirt between the PCB top and the lid plate
    translate([din_face_x, -(din_clear_y + oled_skirt_t), pcb_t + 0.1])
        cube([bx1 + clr + wall - din_face_x, oled_skirt_t, ceiling_z - pcb_t - 0.1 + 0.01]);
}

module thumb_recess() {
    x_out = bx1 + clr + wall;
    translate([x_out - thumb_depth, -thumb_y1, -1.5]) cube([thumb_depth + 1, thumb_y1 - thumb_y0, top_z - 1.0 + 1.5]);
}


// ---------------------------------------------------------------------
// TRAY
// ---------------------------------------------------------------------
module standoffs() {
    for (h = holes) translate([h[0], -h[1], -standoff_h - 0.01]) cylinder(d = standoff_d, h = standoff_h + 0.01);
}

module screw_holes() {
    for (h = holes) translate([h[0], -h[1], 0]) {
        translate([0, 0, bottom_z - 1]) cylinder(d = screw_clear_d, h = 20);
        // 90 deg countersink (prints without support, floor on the bed)
        translate([0, 0, bottom_z - 0.01]) cylinder(d1 = csk_d, d2 = screw_clear_d, h = (csk_d - screw_clear_d) / 2);
        translate([0, 0, bottom_z - 1]) cylinder(d = csk_d, h = 1.01);
    }
}

module usb_cuts() {
    y_in = by1 + clr_bottom;
    for (i = [0 : len(usb_x) - 1]) {
        x = usb_x[i];
        // through opening
        translate([x, -y_in + 1, usb_zc]) rotate([90, 0, 0]) linear_extrude(wall + 3) rrect_c(usb_w, usb_h, usb_r);
        // engraved label under the opening
        translate([x, -(y_in + wall) + engrave, bottom_z + 2.3]) rotate([90, 0, 0])
            linear_extrude(engrave + 1)
                text(usb_lbl[i], size = 2.6, font = "Liberation Sans:style=Bold", halign = "center", valign = "bottom");
    }
    // outer pocket for the plug overmolds (leaves wall - usbp_depth), shared by both plugs
    translate([0, -(y_in + wall - usbp_depth), usb_zc]) rotate([90, 0, 0])
        linear_extrude(usbp_depth + 1) hull() for (x = usb_x) translate([x, 0]) rrect_c(usbp_w, usbp_h, usbp_r);
}

module s1_slot() {
    x_in = bx1 + clr;
    translate([x_in - 1, -(s1_y1 + s1_slot_clr), s1_slot_z0])
        cube([wall + 3, s1_y1 - s1_y0 + 2 * s1_slot_clr, 30]);
}

module oled_post() {
    translate([oled_post[0], -oled_post[1], -standoff_h - 0.01])
        cylinder(d = oled_post_d, h = standoff_h + oled_bottom - oled_post_gap + 0.01);
}

module tray() {
    difference() {
        union() {
            difference() {
                translate([0, 0, bottom_z]) linear_extrude(split_z - joint_gap - bottom_z) outer2d();
                translate([0, 0, -standoff_h]) linear_extrude(50) cavity2d();
            }
            standoffs();
            oled_post();
            tray_notch_closer();
        }
        screw_holes();
        usb_cuts();
        s1_slot();
        thumb_recess();
        din_clear();
    }
}

// ---------------------------------------------------------------------
// LID
// ---------------------------------------------------------------------
module kslab(r4, z, h = 0.01) {   // thin slab from a KiCad rectangle [x0,y0,x1,y1]
    translate([0, 0, z]) linear_extrude(h) krect(r4[0], r4[1], r4[2], r4[3]);
}
function grow(r4, d) = [r4[0] - d, r4[1] - d, r4[2] + d, r4[3] + d];

win = [win_x0, win_y0, win_x1, win_y1];
module oled_window() {   // through the lid top, 45 deg chamfer towards the outside
    hull() {
        kslab(win, ceiling_z - 0.5, 0.5);
        kslab(grow(win, top_t), top_z + 0.01);
    }
}

// DIN hump: the lid rises around J3 only
module hump2d() { intersection() { cavity2d(); krect(hump_cav[0], hump_cav[1], hump_cav[2], hump_cav[3]); } }
module hump_solid() { translate([0, 0, split_z]) linear_extrude(hump_top_z - split_z) offset(r = wall) hump2d(); }
module hump_void()  { translate([0, 0, split_z - 1]) linear_extrude(hump_ceiling_z - split_z + 1) hump2d(); }

module lip_exclusion() {
    // no lip along the right side (OLED, thumb-wheel) nor around the DIN socket
    krect(176, 0, 250, 100);
    krect(hump_cav[0] - wall - 1, 0, 250, hump_cav[3] + wall + 1);
}
module lid_lip() {
    // the lip itself, entering the tray
    translate([0, 0, split_z - lip_h]) linear_extrude(lip_h + 0.01) difference() {
        offset(delta = -lip_clr) cavity2d();
        offset(delta = -lip_clr - lip_t) cavity2d();
        lip_exclusion();
    }
    // thickened wall above the joint that carries the lip, with a stepped
    // 45 deg transition back to the normal wall; only needed when the lid
    // has side walls above the joint (with ceiling_z = split_z the lip hangs
    // directly under the top plate)
    steps = 6;
    w = lip_clr + lip_t;
    if (ceiling_z > split_z + 0.01) for (i = [0 : steps]) {
        z0 = split_z + (i == 0 ? 0 : 1.0 + (i - 1) * w / steps);
        h  = (i == 0 ? 1.0 : w / steps) + 0.01;
        translate([0, 0, z0]) linear_extrude(h) difference() {
            cavity2d();
            offset(delta = -w * (1 - (i == 0 ? 0 : (i - 0.5) / steps))) cavity2d();
            lip_exclusion();
        }
    }
}

module lid_columns() {
    for (h = holes) translate([h[0], -h[1], pcb_t]) cylinder(d = column_d, h = ceiling_z - pcb_t + 0.01);
}
module lid_column_holes() {
    for (h = holes) translate([h[0], -h[1], pcb_t - 0.01]) {
        cylinder(d = use_inserts ? insert_d : selftap_d, h = insert_hole_l);
        cylinder(d1 = (use_inserts ? insert_d : selftap_d) + 0.8, d2 = (use_inserts ? insert_d : selftap_d), h = 0.4); // lead-in
    }
}



module s1_tab() {
    // fills the tray slot above the wheel; 0.2 mm side clearance
    x_in = bx1 + clr;
    c = 0.2;
    translate([x_in, -(s1_y1 + s1_slot_clr) + c, s1_tab_z0])
        cube([wall, s1_y1 - s1_y0 + 2 * s1_slot_clr - 2 * c, split_z - s1_tab_z0 + 0.01]);
}

module lid_text() {
    if (lid_text != "")
        translate([134, -64, top_z - engrave]) linear_extrude(engrave + 1)
            text(lid_text, size = 5.5, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
}

module lid() {
    difference() {
        union() {
            difference() {
                translate([0, 0, split_z]) linear_extrude(top_z - split_z) outer2d();
                translate([0, 0, split_z - 1]) linear_extrude(ceiling_z - split_z + 1) cavity2d();
            }
            lid_lip();
            lid_columns();
            s1_tab();
            hump_solid();
            lid_notch_skirt();
        }
        lid_column_holes();
        hump_void();
        din_clear();
        thumb_recess();
        oled_window();
        lid_text();
    }
}

// ---------------------------------------------------------------------
// Output selection
// ---------------------------------------------------------------------
cx = (bx0 + bx1) / 2;  cy = -(by0 + by1) / 2;

// The case is modelled in the board's original frame (DIN socket facing +X). The board was
// then turned 90 deg counter-clockwise (DIN facing up, -Y in KiCad): this puts the case
// back on the board's current KiCad coordinates (bounding box x 100..164.5, y 25..114.1).
// The pivot is the old board centre (148.45, 56.35): it stays fixed when the board grows.
module board_frame() { translate([132.25, -66.55, 0]) rotate([0, 0, 90]) translate([-148.45, 56.35, 0]) children(); }

if (part == "tray") board_frame() tray();
else if (part == "lid") board_frame() lid();
else if (part == "tray_print")       // floor on the bed, centred on the origin
    translate([-cx, -cy, -bottom_z]) tray();
else if (part == "lid_print")        // lid right side up, the 3 columns on the bed: needs supports
    translate([-cx, -cy, -pcb_t]) lid(); // (build plate only) under the flat top, the lip, the tubes and the S1 tab
else if (part == "exploded") board_frame() {
    color("SteelBlue") tray();
    color("LightSteelBlue") translate([0, 0, 30]) lid();
} else board_frame() {
    color("SteelBlue") tray();
    color("LightSteelBlue", 0.6) lid();
}
