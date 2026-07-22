import bpy, bmesh, math

# ---- Parameters (single source of truth) ----
OD        = 80.0   # body outside diameter, mm
H         = 80.0   # body height, mm
WALL      = 3.0    # side wall thickness, mm
FLOOR     = 4.0    # floor thickness, mm — thicker than the wall, it takes the set-down
SEG       = 96     # cylinder segments — kills visible faceting at 80mm dia

# Handle: a D-loop in the XZ plane, hung off the +X side. The loop's circle is centred
# OUTSIDE the wall by HANDLE_OFF, so its left arc buries into the solid body and the
# bore (cut afterwards) trims it back to clean roots at the wall.
HANDLE_R    = 26.0  # loop centreline radius, mm
HANDLE_OFF  = 12.0  # loop centre, measured out from the wall (x = OD/2 + this), mm
HANDLE_T_R  = 12.0  # strap section, radial (in the loop's plane), mm
HANDLE_T_Y  = 8.0   # strap section, across (Y), mm
HANDLE_CZ   = H/2   # loop centre height, mm
HSEG_MAJ  = 72     # loop segments round the ring
HSEG_MIN  = 32     # segments round the strap section

RIM_FIL   = 1.0    # rim fillet, mm — NOT the planned 2.0: a 2mm bevel on the inner AND
                   # outer rim edge is 4mm of a 3mm wall. 1.0 is what the wall affords.
RIM_SEG   = 4      # rim fillet segments
OVER      = 10.0   # boolean overshoot, mm
NAME      = "Mug"

HANDLE_CX = OD/2 + HANDLE_OFF

# Checker reads raw coordinates as millimetres -> build at mm magnitude, no rescale.

def purge(*names):
    for n in names:
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)

# default Blender startup cube + old scratch object ride along on export if left in
purge("Cube", "benchtest")
purge(NAME, "_body", "_handle", "_bore")

def apply_bool(host, tool, op):
    m = host.modifiers.new("bool", 'BOOLEAN')
    m.operation = op
    m.object = tool
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = host
    bpy.ops.object.modifier_apply(modifier="bool")
    bpy.data.objects.remove(tool, do_unlink=True)

# --- body: solid cylinder, base on z=0 ---
bpy.ops.mesh.primitive_cylinder_add(vertices=SEG, radius=OD/2, depth=H,
                                    location=(0, 0, H/2))
body = bpy.context.active_object
body.name = "_body"

# --- handle: torus rotated into the XZ plane, section squashed to HANDLE_T_Y across ---
bpy.ops.mesh.primitive_torus_add(major_radius=HANDLE_R, minor_radius=HANDLE_T_R/2,
                                 major_segments=HSEG_MAJ, minor_segments=HSEG_MIN,
                                 location=(HANDLE_CX, 0, HANDLE_CZ),
                                 rotation=(math.pi/2, 0, 0))
handle = bpy.context.active_object
handle.name = "_handle"
bpy.context.view_layer.objects.active = handle
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
handle.scale = (1.0, HANDLE_T_Y/HANDLE_T_R, 1.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Union onto the SOLID body first. The loop's buried arc is harmless inside solid
# material, and the bore below trims it to clean roots for free.
apply_bool(body, handle, 'UNION')

# --- bore: from z=FLOOR up through the rim ---
bore_d = H - FLOOR + OVER
bpy.ops.mesh.primitive_cylinder_add(vertices=SEG, radius=OD/2 - WALL, depth=bore_d,
                                    location=(0, 0, FLOOR + bore_d/2))
bore = bpy.context.active_object
bore.name = "_bore"
apply_bool(body, bore, 'DIFFERENCE')

# Bake the transforms down so local coords == world coords. Without this the cylinder's
# origin sits at z=H/2 and every coordinate test below hunts in the wrong space.
# transform_apply works on the SELECTED objects, not the active one — the boolean's tool
# object takes the selection with it, so select the body back or this silently no-ops.
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# --- rim fillet: both circles at z=H (outer edge + bore lip) ---
me = body.data
bm = bmesh.new(); bm.from_mesh(me)
t = 0.01
rim = [e for e in bm.edges
       if abs(e.verts[0].co.z - H) < t and abs(e.verts[1].co.z - H) < t]
bmesh.ops.bevel(bm, geom=rim, offset=RIM_FIL, offset_type='OFFSET',
                segments=RIM_SEG, profile=0.5, affect='EDGES')
bm.to_mesh(me); bm.free()

body.name = NAME
bpy.context.view_layer.objects.active = body

# --- receipts ---
inner_r = OD/2 - WALL
vol = math.pi * inner_r**2 * (H - FLOOR) / 1000.0   # mm^3 -> ml
root_dz = 2 * HANDLE_R * math.sin(math.acos(-HANDLE_OFF/HANDLE_R)) \
          if abs(HANDLE_OFF) < HANDLE_R else 0.0
gap_x = (HANDLE_CX + HANDLE_R - HANDLE_T_R/2) - OD/2
gap_z = 2 * (HANDLE_R - HANDLE_T_R/2)
print(f"  body   D{OD} x {H}mm, wall {WALL}, floor {FLOOR}")
print(f"  handle loop R{HANDLE_R} at x={HANDLE_CX}, section {HANDLE_T_R}x{HANDLE_T_Y}mm")
print(f"  roots  {root_dz:.1f}mm apart vertically")
print(f"  finger gap ~{gap_x:.0f} x {gap_z:.0f}mm")
print(f"  brim volume ~{vol:.0f} ml")
print(f"  rim fillet R{RIM_FIL} on {len(rim)} edges")
print(f"BUILT: {NAME}")
