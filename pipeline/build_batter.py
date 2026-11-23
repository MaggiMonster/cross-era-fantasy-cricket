"""Build rigged batters on an MPFB (MakeHuman) body, with kit and scripted batting clips.

Needs the free MPFB extension. Run from the repo root (no --factory-startup, which would
disable the extension):
  blender --online-mode --command extension install --sync --enable mpfb
  blender --background --python pipeline/build_batter.py -- tendulkar kohli

Writes, outside git:
  ~/cricket-project/assets/characters/<player>.glb            body, kit, bat, rig
  ~/cricket-project/assets/animations/scripted/<player>.glb   one clip per action

Character space (Blender): chest faces -Y (off side), the bowler is at +X, Z is up.
All clips are 30 fps and 30 frames, with bat contact at frame 12 (0.4 s).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

ASSETS = Path.home() / "cricket-project" / "assets"
FPS = 30
CONTACT_FRAME = 12
LAST_FRAME = 30
REFERENCE_HEIGHT = 1.75
SHOTS = ("leave", "defend", "work", "drive", "cut", "pull", "sweep", "loft")
VARIANTS = ("defend_back", "work_back", "drive_back", "cut_front", "pull_front")
BACK_FOOT_CLIPS = {"cut", "pull", "defend_back", "work_back", "drive_back"}  # Same list as web/src/shots.js.

PLAYERS = {
    "tendulkar": {
        "height": 1.65, "shirt": 0x1d4ed8, "trim": 0xf59e0b, "skin": 0x9a6a48,
        "macro": {"gender": 1.0, "age": 0.55, "muscle": 0.68, "weight": 0.56, "height": 0.42, "proportions": 0.55,
                  "race": {"asian": 0.85, "caucasian": 0.10, "african": 0.05}},
        # Compact: narrow base, low crouch, short controlled backlift.
        "stance_width": 0.82, "crouch": 0.075, "backlift": 0.72, "follow": 0.84, "wrist": 0.8,
    },
    "kohli": {
        "height": 1.75, "shirt": 0x1e40af, "trim": 0xf97316, "skin": 0xa87652,
        "macro": {"gender": 1.0, "age": 0.48, "muscle": 0.78, "weight": 0.45, "height": 0.55, "proportions": 0.65,
                  "race": {"asian": 0.80, "caucasian": 0.15, "african": 0.05}},
        # Upright, wider base, high backlift, full follow-through and a stronger wrist.
        "stance_width": 1.0, "crouch": 0.04, "backlift": 1.18, "follow": 1.08, "wrist": 1.2,
    },
}

GRIP = Vector((0.03, -0.235, 0.895))  # Top of the bat handle at rest, for a 1.75 m player.
FINGERS = ("index", "middle", "ring", "pinky")
SPINE = ("spine_01", "spine_02", "spine_03")
_last_rotation: dict[str, Quaternion] = {}


def rgb(value: int) -> tuple[float, float, float, float]:
    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (*(linear(((value >> s) & 255) / 255) for s in (16, 8, 0)), 1.0)


def material(name: str, color: int, roughness: float = 0.6) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes["Principled BSDF"]
    node.inputs["Base Color"].default_value = rgb(color)
    node.inputs["Roughness"].default_value = roughness
    return mat


def clear_scene() -> None:
    """Empty the file without resetting preferences, which would unload MPFB."""
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
        for item in list(collection):
            collection.remove(item)


def group_centre(obj, name: str) -> Vector | None:
    group = obj.vertex_groups.get(name)
    if group is None:
        return None
    points = [v.co for v in obj.data.vertices if any(g.group == group.index and g.weight > 0.5 for g in v.groups)]
    return sum(points, Vector()) / len(points) if points else None


def make_human(player: str):
    """An MPFB body at the player's height, with helpers removed and transforms applied."""
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService
    from bl_ext.blender_org.mpfb.services.targetservice import TargetService

    p = PLAYERS[player]
    macro = TargetService.get_default_macro_info_dict()
    macro.update(p["macro"])
    body = HumanService.create_human(
        mask_helpers=False, detailed_helpers=True, extra_vertex_groups=True, feet_on_ground=True,
        scale=0.1, macro_detail_dict=macro,
    )
    arm = HumanService.add_builtin_rig(body, "game_engine", import_weights=True)
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    if body.data.shape_keys:
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    for modifier in list(body.modifiers):
        if modifier.type == "MASK":
            body.modifiers.remove(modifier)

    eyes = [group_centre(body, f"joint-{side}-eye") for side in "lr"]
    drop = [g.index for g in body.vertex_groups if g.name in ("HelperGeometry", "JointCubes") or g.name.startswith("joint-")]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    layer = bm.verts.layers.deform.verify()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if any(i in v[layer] and v[layer][i] > 0.5 for i in drop)], context="VERTS")
    bm.to_mesh(body.data)
    bm.free()

    height = max(v.co.z for v in body.data.vertices) - min(v.co.z for v in body.data.vertices)
    scale = Matrix.Scale(p["height"] / height, 4)
    body_world, arm_world = body.matrix_world.copy(), arm.matrix_world.copy()
    body.parent = None
    body.matrix_world, arm.matrix_world = scale @ body_world, scale @ arm_world
    eyes = [body_world @ e if e is not None else None for e in eyes]
    eyes = [scale @ e if e is not None else None for e in eyes]
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (body, arm):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    body.parent = arm
    body.matrix_parent_inverse = Matrix.Identity(4)
    return body, arm, eyes


def hand_frame(arm, side: str) -> tuple[Vector, Vector, Vector]:
    """Rest-pose finger direction, thumb direction and palm normal of one hand."""
    bones = arm.data.bones
    wrist = bones[f"hand_{side}"].head_local
    fingers = (bones[f"middle_01_{side}"].head_local - wrist).normalized()
    thumb = bones[f"thumb_01_{side}"].head_local - wrist
    thumb = (thumb - fingers * thumb.dot(fingers)).normalized()
    palm = fingers.cross(thumb) * (1 if side == "l" else -1)
    return fingers, thumb, palm


def add_controls(arm, s: float) -> None:
    """Add bat, foot and hand controls to the MPFB game rig."""
    frames = {side: hand_frame(arm, side) for side in "lr"}
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bones = arm.data.edit_bones
    grip = GRIP * s

    bat = bones.new("bat")
    bat.head, bat.tail = grip, grip - Vector((0, 0, 0.84))
    bat.roll = 0
    sweet = bones.new("bat_sweet")
    sweet.head, sweet.tail = grip - Vector((0, 0, 0.66)), grip - Vector((0, 0, 0.72))
    sweet.roll = 0
    sweet.parent = bat

    # Both hands take the same diagonal grip; the top hand is nearer the handle's end.
    wanted_fingers = Vector((0, -0.55, -0.83)).normalized()
    wanted_thumb = Vector((0, -0.83, 0.55)).normalized()
    wanted = Matrix((wanted_fingers, wanted_thumb, wanted_fingers.cross(wanted_thumb))).transposed()
    for side, drop in (("l", 0.045), ("r", 0.155)):
        fingers, thumb, _ = frames[side]
        rest = Matrix((fingers, thumb, fingers.cross(thumb))).transposed()
        turn = (wanted @ rest.inverted()).to_quaternion()
        hand = bones[f"hand_{side}"]
        palm = wanted_fingers.cross(wanted_thumb) * (1 if side == "l" else -1)
        wrist = grip - Vector((0, 0, drop)) - wanted_fingers * 0.085 * s - palm * 0.028
        control = bones.new(f"hand_ik_{side}")
        control.head, control.tail = Vector(), Vector((0, 0.07, 0))
        control.matrix = Matrix.Translation(wrist) @ (turn @ hand.matrix.to_quaternion()).to_matrix().to_4x4()
        control.parent = bat
        control.use_deform = False

        foot = bones[f"foot_{side}"]
        foot_control = bones.new(f"foot_ik_{side}")
        foot_control.head, foot_control.tail, foot_control.roll = foot.head, foot.tail, foot.roll
        foot_control.use_deform = False
    if "Root" in bones:
        bones["Root"].use_deform = False
    bpy.ops.object.mode_set(mode="OBJECT")

    for side in "lr":
        for bone, target in ((f"lowerarm_{side}", f"hand_ik_{side}"), (f"calf_{side}", f"foot_ik_{side}")):
            ik = arm.pose.bones[bone].constraints.new("IK")
            ik.target, ik.subtarget, ik.chain_count = arm, target, 2
        for bone, target in ((f"hand_{side}", f"hand_ik_{side}"), (f"foot_{side}", f"foot_ik_{side}")):
            copy = arm.pose.bones[bone].constraints.new("COPY_ROTATION")
            copy.target, copy.subtarget = arm, target


def dress_body(body, arm, player: str):
    """Turn the bare body into kit: smooth the clothed areas, push them out, assign colours."""
    p = PLAYERS[player]
    mats = {
        "skin": material("skin", p["skin"], 0.55), "shirt": material("shirt", p["shirt"], 0.6),
        "trim": material("trim", p["trim"], 0.5), "trousers": material("trousers", 0x172554, 0.75),
        "gloves": material("gloves", 0xe8edf3, 0.6), "shoes": material("shoes", 0xf8fafc, 0.45),
    }
    names = list(mats)
    body.data.materials.clear()
    for mat in mats.values():
        body.data.materials.append(mat)

    bones = arm.data.bones
    waist = bones["spine_01"].head_local.z + 0.015
    collar = bones["neck_01"].head_local.z + 0.018
    groups = {g.index: g.name for g in body.vertex_groups}

    def dominant(vertex) -> str:
        best, weight = "", 0.0
        for g in vertex.groups:
            name = groups.get(g.group, "")
            if name in bones and g.weight > weight:
                best, weight = name, g.weight
        return best

    owner = [dominant(v) for v in body.data.vertices]

    def region(co: Vector, bone: str) -> str:
        if bone == "head":
            return "skin"
        if bone == "neck_01":
            return "trim" if co.z < collar else "skin"
        if bone.startswith(("hand_", "index", "middle", "ring", "pinky", "thumb")):
            return "gloves"
        if bone.startswith(("foot_", "ball_")):
            return "shoes"
        if bone.startswith("lowerarm"):
            return "skin"
        if bone.startswith("upperarm"):
            b = bones[bone]
            f = (co - b.head_local).dot(b.tail_local - b.head_local) / (b.tail_local - b.head_local).length_squared
            return "shirt" if f < 0.68 else "trim" if f < 0.75 else "skin"
        if bone.startswith(("thigh", "calf")):
            return "trousers"
        return "shirt" if co.z >= waist else "trousers"

    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    for face in bm.faces:
        votes = [owner[v.index] for v in face.verts]
        face.material_index = names.index(region(face.calc_center_median(), max(set(votes), key=votes.count)))

    clothed = {"shirt", "trim", "trousers", "shoes"}
    soft = [v for v in bm.verts if v.link_faces and all(names[f.material_index] in clothed for f in v.link_faces)]
    for _ in range(10):
        bmesh.ops.smooth_vert(bm, verts=soft, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    push = {"shirt": 0.010, "trim": 0.012, "trousers": 0.016, "gloves": 0.005, "shoes": 0.010, "skin": 0.0}
    moves = []
    for v in bm.verts:
        if v.link_faces:
            amount = max(push[names[f.material_index]] for f in v.link_faces)
            moves.append((v, v.normal * amount))
    for v, move in moves:
        v.co += move
    bm.to_mesh(body.data)
    bm.free()
    body.data.polygons.foreach_set("use_smooth", [True] * len(body.data.polygons))
    body.data.update()

    # The head is a separate object so a FaceBuilder head can replace it.
    head = body.copy()
    head.data = body.data.copy()
    head.name = head.data.name = "Head"
    bpy.context.collection.objects.link(head)
    body.name = body.data.name = "Body"
    head_faces = {f.index for f in body.data.polygons if max(
        set(owner[i] for i in f.vertices), key=[owner[i] for i in f.vertices].count) == "head"}
    for obj, remove_head in ((body, True), (head, False)):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        doomed = [f for f in bm.faces if (f.index in head_faces) == remove_head]
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bm.to_mesh(obj.data)
        bm.free()
    head.data.materials.clear()
    head.data.materials.append(mats["skin"])
    return head


class MeshBuilder:
    """Lofted gear (pads, helmet, bat), each piece bound to a short list of bones."""

    def __init__(self, arm):
        self.arm = arm
        self.bm = bmesh.new()
        self.materials: list[bpy.types.Material] = []
        self.bind: list[tuple[str, ...]] = []
        self.segments = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}

    def _slot(self, mat) -> int:
        if mat not in self.materials:
            self.materials.append(mat)
        return self.materials.index(mat)

    def loft(self, rings, mat, bones, segments: int = 20, ridges: int = 0) -> None:
        """rings: (centre, side axis, forward axis, side radius, forward radius)."""
        rows = []
        for centre, x, y, rx, ry in rings:
            row = []
            for i in range(segments):
                a = 2 * math.pi * i / segments
                bump = 1 + (0.09 * abs(math.cos(ridges * a / 2)) if ridges and math.sin(a) < 0 else 0)
                row.append(self.bm.verts.new(centre + x * (rx * math.cos(a)) + y * (ry * math.sin(a) * bump)))
                self.bind.append(tuple(bones))
            rows.append(row)
        slot = self._slot(mat)
        for lower, upper in zip(rows, rows[1:]):
            for i in range(segments):
                k = (i + 1) % segments
                self.bm.faces.new((lower[i], lower[k], upper[k], upper[i])).material_index = slot
        for row in (rows[0], rows[-1][::-1]):
            self.bm.faces.new(row).material_index = slot

    def dome(self, centre, radii, mat, bones, low: float = 0.0) -> None:
        rings = []
        for n in range(11):
            v = low + (1 - low) * (n + 0.02) / 10.04
            w = math.sqrt(max(1 - v * v, 0.0025))
            rings.append((centre + Vector((0, 0, radii[2] * v)), Vector((1, 0, 0)), Vector((0, 1, 0)), radii[0] * w, radii[1] * w))
        self.loft(rings, mat, bones, 24)

    def box(self, low, high, mat, bones) -> None:
        (lx, ly, lz), (hx, hy, hz) = low, high
        points = [(lx, ly, lz), (hx, ly, lz), (hx, hy, lz), (lx, hy, lz), (lx, ly, hz), (hx, ly, hz), (hx, hy, hz), (lx, hy, hz)]
        verts = [self.bm.verts.new(q) for q in points]
        self.bind += [tuple(bones)] * 8
        slot = self._slot(mat)
        for f in ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.bm.faces.new([verts[i] for i in f]).material_index = slot

    def _weights(self, point: Vector, bones) -> list[tuple[str, float]]:
        if len(bones) == 1:
            return [(bones[0], 1.0)]
        scored = []
        for name in bones:
            a, b = self.segments[name]
            ab = b - a
            f = max(0.0, min(1.0, (point - a).dot(ab) / ab.length_squared))
            scored.append((name, (point - (a + ab * f)).length))
        scored.sort(key=lambda x: x[1])
        (n1, d1), (n2, d2) = scored[:2]
        share = max(0.0, 0.5 - (d2 - d1) / 0.12)
        return [(n1, 1 - share), (n2, share)] if share > 0 else [(n1, 1.0)]

    def finish(self, name: str) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(name)
        self.bm.normal_update()
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.verts.ensure_lookup_table()
        points = [v.co.copy() for v in self.bm.verts]
        self.bm.to_mesh(mesh)
        self.bm.free()
        for mat in self.materials:
            mesh.materials.append(mat)
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        for index, (point, bones) in enumerate(zip(points, self.bind)):
            for bone, weight in self._weights(point, bones):
                group = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
                group.add([index], weight, "REPLACE")
        obj.parent = self.arm
        obj.modifiers.new("rig", "ARMATURE").object = self.arm
        return obj


def build_gear(arm, head, eyes, s: float) -> None:
    pads = material("pads", 0xf1f5f9, 0.65)
    helmet = material("helmet", 0x1e3a8a, 0.3)
    grille = material("grille", 0x94a3b8, 0.3)
    willow = material("willow", 0xe9cf9b, 0.5)
    grip = material("grip", 0x1f2937, 0.85)
    white = material("eye_white", 0xf4f1ea, 0.3)
    iris = material("eye_iris", 0x1c120c, 0.25)
    gear = MeshBuilder(arm)
    bones = arm.data.bones

    for side in "lr":
        knee, ankle = bones[f"calf_{side}"].head_local, bones[f"calf_{side}"].tail_local
        down = (ankle - knee).normalized()
        forward = Vector((0, -1, 0))
        forward = (forward - down * forward.dot(down)).normalized()
        across = down.cross(forward).normalized()
        length = (ankle - knee).length
        profile = [(-0.26, 0.050, 0.040), (-0.16, 0.074, 0.060), (-0.04, 0.084, 0.072), (0.10, 0.080, 0.070),
                   (0.30, 0.078, 0.070), (0.60, 0.070, 0.064), (0.88, 0.062, 0.056), (1.0, 0.052, 0.046)]
        rings = [(knee + down * (f * length) + forward * (0.028 * s), across, forward, rx * s, ry * s) for f, rx, ry in profile]
        gear.loft(rings, pads, (f"calf_{side}", f"thigh_{side}"), 22, ridges=6)

    points = [Vector(v.co) for v in head.data.vertices]
    top = max(q.z for q in points)
    width = max(q.x for q in points) - min(q.x for q in points)
    front = min(q.y for q in points)
    back = max(q.y for q in points)
    eye_z = eyes[0].z if eyes[0] is not None else top - 0.115 * s
    centre = Vector((0, (front + back) / 2 + 0.004, eye_z + 0.018 * s))
    radii = (width / 2 + 0.024, (back - front) / 2 + 0.026, top - centre.z + 0.022)
    gear.dome(centre, radii, helmet, ("head",), low=-0.12)
    peak_y = centre.y - radii[1]
    gear.box((-0.085 * s, peak_y - 0.055 * s, centre.z - 0.004), (0.085 * s, peak_y + 0.03 * s, centre.z + 0.006), helmet, ("head",))
    chin = eye_z - 0.125 * s
    bar_y = front - 0.028 * s
    for f in (0.0, 0.34, 0.67):
        z = chin + (centre.z - chin) * f
        gear.box((-0.075 * s, bar_y - 0.004, z), (0.075 * s, bar_y + 0.004, z + 0.006), grille, ("head",))
    for x in (-0.07, -0.024, 0.024, 0.07):
        gear.box(((x - 0.003) * s, bar_y - 0.004, chin), ((x + 0.003) * s, bar_y + 0.004, centre.z), grille, ("head",))

    for eye in eyes:
        if eye is not None:
            gear.dome(eye - Vector((0, 0, 0.012 * s)), (0.0125 * s, 0.0125 * s, 0.0125 * s), white, ("head",), low=-0.99)
            gear.dome(eye + Vector((0, -0.0105 * s, -0.005 * s)), (0.0055 * s, 0.003 * s, 0.0055 * s), iris, ("head",), low=-0.99)

    top_grip = GRIP * s
    up, side_axis, depth = Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))
    handle = [(top_grip + up * 0.035, 0.015), (top_grip + up * 0.02, 0.0175), (top_grip - up * 0.26, 0.0175), (top_grip - up * 0.30, 0.020)]
    gear.loft([(c, side_axis, depth, r, r) for c, r in handle], grip, ("bat",), 12)
    blade = [(-0.285, 0.018, 0.016), (-0.31, 0.046, 0.024), (-0.36, 0.053, 0.029), (-0.55, 0.054, 0.033),
             (-0.72, 0.054, 0.034), (-0.84, 0.053, 0.030), (-0.895, 0.050, 0.022), (-0.905, 0.034, 0.012)]
    gear.loft([(top_grip + up * z + depth * (-0.006), side_axis, depth, w, d) for z, w, d in blade], willow, ("bat",), 16)
    gear.finish("Gear")


def set_bone(pb, frame: int, world_rot: Quaternion | None = None, offset: Vector | None = None) -> None:
    pb.rotation_mode = "QUATERNION"
    rest = pb.bone.matrix_local.to_quaternion()
    if world_rot is not None:
        local = rest.inverted() @ world_rot @ rest
        previous = _last_rotation.get(pb.name)
        if previous is not None and previous.dot(local) < 0:
            local.negate()  # Keeps every swing on the short way round.
        _last_rotation[pb.name] = local.copy()
        pb.rotation_quaternion = local
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    if offset is not None:
        pb.location = rest.inverted() @ offset
        pb.keyframe_insert("location", frame=frame)


def turn(yaw: float = 0, lean: float = 0, side: float = 0) -> Quaternion:
    """Degrees. yaw: chest towards the bowler. lean: forward. side: towards the bowler."""
    z = Quaternion((0, 0, 1), math.radians(yaw))
    y = Quaternion((0, 1, 0), math.radians(side))
    x = Quaternion((1, 0, 0), math.radians(lean))
    return z @ y @ x


def bat_rotation(direction, face) -> Quaternion:
    """Blade points along `direction`, with its hitting face towards `face`."""
    d = Vector(direction).normalized()
    n = Vector(face)
    n = (n - d * n.dot(d)).normalized()
    z = -d
    y = z.cross(n)
    return Matrix((n, y, z)).transposed().to_quaternion()


def mix(a: dict, b: dict, t: float) -> dict:
    """A pose part way between two poses."""
    out = {}
    for key in a:
        x, y = a[key], b.get(key, a[key])
        out[key] = tuple(p + (q - p) * t for p, q in zip(x, y)) if isinstance(x, tuple) else x + (y - x) * t
    return out


def stance(p: dict) -> dict:
    w = p["stance_width"]
    return {
        "hips": (0.0, -0.015, -p["crouch"]), "yaw": 14.0, "lean": 16.0, "chest": 6.0,
        "front": (0.13 + 0.09 * w, -0.01, 0.0, 10.0), "back": (-0.11 - 0.09 * w, 0.02, 0.0, -6.0),
        "grip": (0.03, -0.235, 0.895), "bat": (-0.12, -0.05, -1.0), "face": (1.0, 0.0, 0.0),
    }


def trigger(p: dict) -> dict:
    """The small back-and-across press every batter makes as the ball is released."""
    base = stance(p)
    x, y, z, yaw = base["back"]
    return {**base, "back": (x + 0.035, y - 0.03, z, yaw), "hips": (-0.015, -0.025, -p["crouch"] - 0.012),
            "grip": (0.0, -0.215, 0.93), "bat": (-0.34, -0.05, -0.92)}


def backlift(p: dict, **extra) -> dict:
    h = p["backlift"]
    pose = {
        **trigger(p), "chest": 0.0, "yaw": 8.0, "hips": (-0.03, -0.02, -p["crouch"] - 0.012),
        "grip": (-0.10 - 0.05 * h, -0.17, 0.98 + 0.18 * h), "bat": (-0.84, -0.04, -0.20 + 0.74 * h),
        "face": (0.25, -0.95, 0.10),
    }
    return {**pose, **extra}


def timeline(p, top, hit, through, finish, down: float = 0.55) -> dict[int, dict]:
    """Stance, trigger, top of the backlift, downswing, contact, follow-through, finish."""
    downswing = mix(top, hit, down)
    gx, gy, gz = downswing["grip"]
    downswing["grip"] = (gx, gy - 0.035, gz + 0.02)  # The hands arc out rather than cutting the corner.
    return {0: stance(p), 3: trigger(p), 8: top, 10: downswing, CONTACT_FRAME: hit, 16: through, 23: finish, LAST_FRAME: finish}


def shot_keys(shot: str, p: dict) -> dict[int, dict]:
    base, up, f, w = stance(p), backlift(p), p["follow"], p["wrist"]
    step = lambda x, y=-0.04, yaw=24.0: (x, y, 0.0, yaw)
    if shot == "leave":
        lifted = {**up, "grip": (-0.03, -0.08, 1.40), "bat": (-0.42, 0.08, 0.90), "face": (0.2, -0.95, 0.2), "lean": 10.0,
                  "front": step(0.40), "hips": (0.10, -0.01, -0.09), "yaw": 6.0}
        return {0: base, 3: trigger(p), 8: mix(up, lifted, 0.6), CONTACT_FRAME: lifted,
                20: {**lifted, "hips": (0.10, -0.01, -0.08)}, LAST_FRAME: {**lifted, "hips": (0.08, -0.01, -0.07)}}
    if shot == "defend":
        hit = {**base, "hips": (0.17, -0.03, -0.14), "yaw": 26.0, "lean": 24.0, "chest": 8.0, "front": step(0.56),
               "grip": (0.44, -0.28, 0.76), "bat": (-0.26, -0.03, -1.0), "face": (1.0, 0.0, -0.18)}
        short = backlift(p, grip=(-0.03, -0.20, 1.02), bat=(-0.55, -0.03, 0.10), face=(0.6, -0.8, 0.0))
        settle = {**hit, "hips": (0.16, -0.03, -0.13), "grip": (0.42, -0.28, 0.77)}
        return {0: base, 3: trigger(p), 8: short, 10: mix(short, hit, 0.6), CONTACT_FRAME: hit, 18: hit, LAST_FRAME: settle}
    if shot == "work":
        hit = {**base, "hips": (0.06, 0.0, -0.09), "yaw": 34.0, "lean": 18.0, "chest": 20.0, "front": step(0.34, 0.03, 30.0),
               "back": (-0.17, 0.05, 0.0, 12.0), "grip": (0.25, -0.22, 0.84), "bat": (0.08, 0.50, -0.86), "face": (0.65, 0.72, 0.1)}
        through = {**hit, "yaw": 44.0, "chest": 27.0, "grip": (0.17, -0.07, 0.94), "bat": (-0.18, 0.80, -0.55),
                   "face": (0.2 - 0.25 * w, 0.8, 0.45)}
        end = {**through, "yaw": 50.0, "chest": 31.0, "grip": (0.09, -0.01, 1.03), "bat": (-0.42, 0.84, -0.22), "face": (-0.2, 0.3, 0.9)}
        return timeline(p, up, hit, through, end)
    if shot == "drive":
        hit = {**base, "hips": (0.24, -0.03, -0.15), "yaw": 22.0, "lean": 26.0, "chest": 10.0, "front": step(0.66),
               "back": (-0.16, 0.03, 0.0, 0.0), "grip": (0.40, -0.30, 0.74), "bat": (0.20, -0.10, -1.0), "face": (1.0, -0.22, 0.05)}
        through = {**hit, "yaw": 30.0, "chest": 16.0, "lean": 18.0, "grip": (0.52, -0.30, 0.86 + 0.36 * f),
                   "bat": (0.72, -0.28, 0.62), "face": (0.55, -0.1, -0.8)}
        end = {**through, "yaw": 42.0, "chest": 24.0, "lean": 10.0, "grip": (0.26, -0.18, 1.08 + 0.36 * f),
               "bat": (-0.42, 0.20, 0.88), "face": (-0.6, -0.7, -0.3)}
        return timeline(p, up, hit, through, end)
    if shot == "cut":
        planted = {**base, "hips": (-0.09, -0.11, -0.10), "yaw": 6.0, "lean": 20.0, "chest": 0.0, "front": (0.22, -0.02, 0.0, 16.0),
                   "back": (-0.23, -0.30, 0.0, -28.0)}
        hit = {**planted, "grip": (0.08, -0.56, 1.06), "bat": (0.28, -0.84, -0.26), "face": (0.75, 0.15, 0.65)}
        through = {**planted, "yaw": -6.0, "chest": -6.0, "grip": (-0.03, -0.53, 1.12), "bat": (-0.38, -0.86, -0.08), "face": (0.35, -0.2, 0.9)}
        end = {**planted, "yaw": -16.0, "chest": -12.0, "grip": (-0.14, -0.47, 1.19), "bat": (-0.84, -0.42, 0.14), "face": (-0.2, -0.3, 0.92)}
        top = {**up, "back": planted["back"], "hips": (-0.07, -0.08, -0.07), "grip": (-0.08, -0.22, 1.30), "bat": (-0.45, -0.25, 0.82)}
        return timeline(p, top, hit, through, end)
    if shot == "pull":
        planted = {**base, "hips": (-0.10, 0.01, -0.08), "lean": 8.0, "yaw": 34.0, "chest": 22.0, "front": (0.27, 0.10, 0.0, 34.0),
                   "back": (-0.24, -0.04, 0.0, 18.0)}
        hit = {**planted, "grip": (0.14, -0.20, 1.22), "bat": (0.74, 0.62, 0.12), "face": (0.65, -0.72, -0.25)}
        through = {**planted, "yaw": 62.0, "chest": 34.0, "grip": (-0.04, 0.20, 1.24), "bat": (-0.42, 0.86, 0.16), "face": (0.45, 0.35, -0.82)}
        end = {**through, "yaw": 74.0, "chest": 40.0, "grip": (-0.20, 0.10, 1.34), "bat": (-0.82, 0.28, 0.46), "face": (-0.25, 0.2, -0.95)}
        return timeline(p, {**up, "hips": (-0.08, 0.0, -0.06)}, hit, through, end)
    if shot == "sweep":
        low = {**base, "hips": (0.14, -0.02, -0.43), "yaw": 26.0, "lean": 34.0, "chest": 12.0, "front": step(0.58, -0.09, 20.0),
               "back": (-0.30, 0.09, 0.0, -18.0), "grip": (0.40, -0.13, 0.46), "bat": (0.62, 0.70, -0.24), "face": (0.72, -0.62, 0.3)}
        through = {**low, "yaw": 40.0, "chest": 20.0, "grip": (0.30, 0.08, 0.53), "bat": (0.15, 0.96, -0.05), "face": (0.75, 0.0, -0.65)}
        end = {**low, "yaw": 50.0, "chest": 26.0, "grip": (0.20, 0.22, 0.60), "bat": (-0.20, 0.95, 0.22), "face": (0.35, 0.2, -0.9)}
        return timeline(p, {**up, "hips": (0.05, -0.01, -0.24), "front": step(0.34, -0.06, 18.0)}, low, through, end)
    if shot == "loft":
        hit = {**base, "hips": (0.26, -0.03, -0.13), "yaw": 24.0, "lean": 18.0, "chest": 12.0, "front": step(0.68),
               "back": (-0.14, 0.03, 0.0, 4.0), "grip": (0.36, -0.27, 0.84), "bat": (0.46, -0.10, -0.86), "face": (0.86, -0.08, 0.46)}
        through = {**hit, "yaw": 38.0, "chest": 22.0, "lean": 6.0, "grip": (0.55, -0.22, 1.42), "bat": (0.72, -0.10, 0.70), "face": (0.65, -0.1, -0.75)}
        end = {**through, "yaw": 56.0, "chest": 32.0, "lean": 0.0, "grip": (0.12, -0.06, 1.60), "bat": (-0.72, 0.10, 0.70), "face": (-0.6, -0.5, -0.6)}
        high = backlift(p, grip=(-0.18, -0.13, 1.22), bat=(-0.72, -0.02, 0.72))
        return timeline(p, high, hit, through, end, down=0.6)
    if shot == "defend_back":
        hit = {**base, "hips": (-0.10, -0.03, -0.07), "yaw": 18.0, "lean": 10.0, "chest": 6.0, "back": (-0.30, -0.06, 0.0, -12.0),
               "grip": (0.12, -0.29, 1.03), "bat": (-0.24, -0.03, -1.0), "face": (1.0, 0.0, -0.14)}
        short = backlift(p, grip=(-0.05, -0.20, 1.12), bat=(-0.55, -0.03, 0.15), face=(0.6, -0.8, 0.0))
        return {0: base, 3: trigger(p), 8: short, 10: mix(short, hit, 0.6), CONTACT_FRAME: hit, 18: hit,
                LAST_FRAME: {**hit, "grip": (0.10, -0.29, 1.04)}}
    if shot == "work_back":
        hit = {**base, "hips": (-0.08, 0.0, -0.07), "yaw": 40.0, "lean": 10.0, "chest": 24.0, "back": (-0.28, 0.02, 0.0, 14.0),
               "grip": (0.10, -0.16, 1.02), "bat": (0.05, 0.58, -0.81), "face": (0.65, 0.72, 0.1)}
        through = {**hit, "yaw": 48.0, "chest": 30.0, "grip": (0.04, -0.02, 1.10), "bat": (-0.28, 0.82, -0.50), "face": (0.0, 0.6, 0.8)}
        end = {**through, "grip": (-0.02, 0.02, 1.16), "bat": (-0.48, 0.80, -0.20), "face": (-0.2, 0.3, 0.9)}
        return timeline(p, up, hit, through, end)
    if shot == "drive_back":
        hit = {**base, "hips": (-0.06, -0.03, -0.06), "yaw": 20.0, "lean": 12.0, "chest": 8.0, "back": (-0.27, -0.05, 0.0, -8.0),
               "grip": (0.24, -0.33, 1.10), "bat": (0.16, -0.14, -1.0), "face": (1.0, -0.2, 0.05)}
        through = {**hit, "yaw": 28.0, "chest": 14.0, "grip": (0.40, -0.30, 1.38), "bat": (0.70, -0.25, 0.60), "face": (0.55, -0.1, -0.8)}
        end = {**through, "yaw": 38.0, "chest": 22.0, "grip": (0.20, -0.18, 1.52), "bat": (-0.40, 0.20, 0.88), "face": (-0.6, -0.7, -0.3)}
        return timeline(p, up, hit, through, end)
    if shot == "cut_front":
        hit = {**base, "hips": (0.16, -0.09, -0.14), "yaw": 10.0, "lean": 24.0, "chest": 2.0, "front": (0.50, -0.24, 0.0, 8.0),
               "grip": (0.32, -0.42, 0.68), "bat": (0.30, -0.78, -0.56), "face": (0.78, 0.12, 0.6)}
        through = {**hit, "yaw": 2.0, "grip": (0.18, -0.48, 0.88), "bat": (-0.32, -0.88, -0.12), "face": (0.35, -0.2, 0.9)}
        end = {**through, "yaw": -8.0, "chest": -6.0, "grip": (0.04, -0.46, 1.10), "bat": (-0.82, -0.44, 0.12), "face": (-0.2, -0.3, 0.92)}
        return timeline(p, up, hit, through, end)
    if shot == "pull_front":
        hit = {**base, "hips": (0.14, 0.02, -0.12), "yaw": 34.0, "lean": 16.0, "chest": 20.0, "front": (0.46, 0.06, 0.0, 30.0),
               "grip": (0.32, -0.14, 0.72), "bat": (0.46, 0.66, -0.60), "face": (0.68, -0.68, -0.2)}
        through = {**hit, "yaw": 56.0, "chest": 30.0, "grip": (0.14, 0.16, 1.06), "bat": (-0.30, 0.92, 0.08), "face": (0.45, 0.35, -0.82)}
        end = {**through, "yaw": 68.0, "chest": 36.0, "grip": (-0.04, 0.10, 1.22), "bat": (-0.78, 0.32, 0.44), "face": (-0.25, 0.2, -0.95)}
        return timeline(p, up, hit, through, end)
    raise ValueError(shot)


def footwork(clip: str, keys: dict[int, dict]) -> dict[int, dict]:
    """Keep the planted foot still after the trigger, and lift the striding foot as it moves."""
    planted, stride = ("front", "back") if clip in BACK_FOOT_CLIPS else ("back", "front")
    x, y, _, _ = keys[3][planted]
    out = {}
    for frame, pose in keys.items():
        pose = dict(pose)
        if frame >= 3:
            pose[planted] = (x, y, 0.0, pose[planted][3])
        lift = {8: 0.035, 10: 0.06}.get(frame, 0.0)
        if lift:
            sx, sy, _, syaw = pose[stride]
            pose[stride] = (sx, sy, lift, syaw)
        out[frame] = pose
    return out


def key_fingers(arm, frame: int) -> None:
    """Close both hands round the handle."""
    bones = arm.pose.bones
    for side in "lr":
        fingers, thumb, palm = hand_frame(arm, side)
        axis = fingers.cross(palm).normalized()
        for finger, spread in zip(FINGERS, (62, 68, 72, 76)):
            for joint, share in zip(("01", "02", "03"), (1.0, 1.15, 0.8)):
                set_bone(bones[f"{finger}_{joint}_{side}"], frame, Quaternion(axis, math.radians(spread * share)))
        for joint, angle in zip(("01", "02", "03"), (18, 28, 34)):
            set_bone(bones[f"thumb_{joint}_{side}"], frame, Quaternion(axis, math.radians(angle)))


def key_pose(arm, frame: int, pose: dict, s: float, ankles: dict[str, Vector]) -> None:
    bones = arm.pose.bones
    set_bone(bones["pelvis"], frame, turn(pose["yaw"], pose["lean"] * 0.40), Vector(pose["hips"]) * s)
    share = turn(pose["chest"] / 3, pose["lean"] * 0.20)
    for name in SPINE:
        set_bone(bones[name], frame, share)
    # The head counter-turns so the eyes stay level and on the bowler.
    total = pose["yaw"] + pose["chest"]
    look = min(82.0, 88.0 - total)
    set_bone(bones["neck_01"], frame, turn(look * 0.38, -pose["lean"] * 0.35))
    set_bone(bones["head"], frame, turn(look * 0.62, -pose["lean"] * 0.48))
    for side, key in (("l", "front"), ("r", "back")):
        x, y, z, foot_yaw = pose[key]
        target = Vector((x * s, y * s, ankles[side].z + z))
        set_bone(bones[f"foot_ik_{side}"], frame, turn(foot_yaw), target - ankles[side])
    set_bone(bones["bat"], frame, bat_rotation(pose["bat"], pose["face"]), (Vector(pose["grip"]) - GRIP) * s)


def fit_grip(arm, frame: int) -> None:
    """Move the bat at this key, keeping its angle, until both arms can reach the handle."""
    bones = arm.pose.bones
    bat = bones["bat"]
    rest = bat.bone.matrix_local.to_quaternion()
    scene = bpy.context.scene
    for _ in range(12):
        scene.frame_set(frame)
        correction = Vector()
        for side in "lr":
            shoulder = bones[f"upperarm_{side}"].head
            gap = bones[f"hand_ik_{side}"].head - shoulder
            reach = (bones[f"upperarm_{side}"].bone.length + bones[f"lowerarm_{side}"].bone.length) * 0.985
            if gap.length > reach:
                pull = -gap.normalized() * (gap.length - reach)
                if pull.length > correction.length:
                    correction = pull
        if correction.length < 1e-4:
            return
        bat.location = rest.inverted() @ ((rest @ bat.location) + correction)
        bat.keyframe_insert("location", frame=frame)


def make_clip(arm, name: str, keys: dict[int, dict], s: float, ankles) -> bpy.types.Action:
    arm.animation_data_create()
    arm.animation_data.action = None
    _last_rotation.clear()
    key_fingers(arm, 0)
    for frame in sorted(keys):
        key_pose(arm, frame, keys[frame], s, ankles)
    for frame in sorted(keys):
        fit_grip(arm, frame)
    action = arm.animation_data.action
    action.name = name
    action.use_fake_user = True
    arm.animation_data.action = None
    return action


def idle_keys(p: dict) -> dict[int, dict]:
    base = stance(p)
    settle = {**base, "hips": (base["hips"][0], base["hips"][1], base["hips"][2] - 0.012)}
    tap = {**settle, "grip": (0.035, -0.235, 0.915), "bat": (-0.10, -0.05, -1.0)}
    return {0: base, 10: settle, 15: tap, 20: settle, LAST_FRAME: base}


def export(path: Path, objects, animations: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
        export_animations=animations, export_animation_mode="ACTIONS", export_force_sampling=True,
        export_frame_step=1, export_skins=True, export_def_bones=True, export_apply=False,
    )


def build(player: str) -> None:
    clear_scene()
    bpy.context.scene.render.fps = FPS
    p = PLAYERS[player]
    s = p["height"] / REFERENCE_HEIGHT
    body, arm, eyes = make_human(player)
    add_controls(arm, s)
    head = dress_body(body, arm, player)
    build_gear(arm, head, eyes, s)
    ankles = {side: arm.data.bones[f"foot_{side}"].head_local.copy() for side in "lr"}
    make_clip(arm, "idle", idle_keys(p), s, ankles)
    for clip in (*SHOTS, *VARIANTS):
        make_clip(arm, clip, footwork(clip, shot_keys(clip, p)), s, ankles)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 0, LAST_FRAME
    scene.frame_set(0)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    export(ASSETS / "characters" / f"{player}.glb", [arm, *meshes], False)
    export(ASSETS / "animations" / "scripted" / f"{player}.glb", [arm, *meshes], True)
    print(f"built {player}: {len(bpy.data.actions)} clips, {sum(len(m.data.polygons) for m in meshes)} faces")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(PLAYERS)
    for name in args:
        build(name)
