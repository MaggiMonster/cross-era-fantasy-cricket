"""Build a rigged batter with kit and scripted batting animations, in Blender.

Run from the repo root:
  blender --background --factory-startup --python pipeline/build_batter.py -- tendulkar kohli

Writes, outside git:
  ~/cricket-project/assets/characters/<player>.glb        body, kit, bat, rig
  ~/cricket-project/assets/animations/scripted/<player>.glb   one clip per action

Character space (Blender): chest faces -Y (off side), the bowler is at +X, Z is up.
All clips are 30 fps, 30 frames, with bat contact at frame 12 (0.4 s).
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

PLAYERS = {
    "tendulkar": {
        "height": 1.65, "build": 1.04, "shirt": 0x1d4ed8, "trim": 0xf59e0b, "skin": 0x9a6a48,
        # Compact: narrow base, low crouch, short controlled backlift.
        "stance_width": 0.82, "crouch": 0.075, "backlift": 0.72, "follow": 0.84,
    },
    "kohli": {
        "height": 1.75, "build": 1.0, "shirt": 0x1e40af, "trim": 0xf97316, "skin": 0xa87652,
        # Upright, wider base, and a high backlift with a full follow-through.
        "stance_width": 1.0, "crouch": 0.04, "backlift": 1.18, "follow": 1.08,
    },
}

JOINTS = {
    "hips": (0, 0, 0.96), "spine": (0, 0, 1.08), "chest": (0, 0, 1.24), "neck": (0, 0, 1.47),
    "head": (0, 0, 1.54), "head_end": (0, 0, 1.75),
    "shoulder": (0.19, 0, 1.42), "elbow": (0.32, 0.035, 1.16), "wrist": (0.40, 0, 0.92),
    "hand_end": (0.42, -0.01, 0.84),
    "hip": (0.10, 0, 0.94), "knee": (0.11, -0.035, 0.52), "ankle": (0.11, 0, 0.095),
    "toe": (0.11, -0.17, 0.025),
}


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


def mirrored(point, side: str) -> Vector:
    return Vector((point[0] * (1 if side == "L" else -1), point[1], point[2]))


def build_armature(s: float) -> bpy.types.Object:
    data = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bones = data.edit_bones

    def bone(name, head, tail, parent=None, deform=True):
        b = bones.new(name)
        b.head, b.tail = Vector(head) * s, Vector(tail) * s
        b.roll = 0
        b.parent = bones[parent] if parent else None
        b.use_deform = deform
        return b

    j = JOINTS
    bone("hips", j["hips"], j["spine"])
    bone("spine", j["spine"], j["chest"], "hips")
    bone("chest", j["chest"], j["neck"], "spine")
    bone("neck", j["neck"], j["head"], "chest")
    bone("head", j["head"], j["head_end"], "neck")
    for side in "LR":
        m = lambda key: mirrored(j[key], side)
        bone(f"upper_arm_{side}", m("shoulder"), m("elbow"), "chest")
        bone(f"forearm_{side}", m("elbow"), m("wrist"), f"upper_arm_{side}")
        bone(f"hand_{side}", m("wrist"), m("hand_end"), f"forearm_{side}")
        bone(f"thigh_{side}", m("hip"), m("knee"), "hips")
        bone(f"shin_{side}", m("knee"), m("ankle"), f"thigh_{side}")
        bone(f"foot_{side}", m("ankle"), m("toe"), f"shin_{side}")
        bone(f"foot_ik_{side}", m("ankle"), m("toe"), deform=False)

    grip = Vector((0.02, -0.25, 0.90))
    bone("bat", grip, grip - Vector((0, 0, 0.84)))
    bone("hand_ik_L", grip + Vector((0, 0, -0.03)), grip + Vector((0, 0, -0.10)), "bat", False)
    bone("hand_ik_R", grip + Vector((0, 0, -0.15)), grip + Vector((0, 0, -0.22)), "bat", False)
    bpy.ops.object.mode_set(mode="OBJECT")

    for side in "LR":
        forearm = arm.pose.bones[f"forearm_{side}"].constraints.new("IK")
        forearm.target, forearm.subtarget, forearm.chain_count = arm, f"hand_ik_{side}", 2
        shin = arm.pose.bones[f"shin_{side}"].constraints.new("IK")
        shin.target, shin.subtarget, shin.chain_count = arm, f"foot_ik_{side}", 2
        foot = arm.pose.bones[f"foot_{side}"].constraints.new("COPY_ROTATION")
        foot.target, foot.subtarget = arm, f"foot_ik_{side}"
    return arm


class MeshBuilder:
    """Lofted tubes and boxes, each bound smoothly to a short list of bones."""

    def __init__(self, arm: bpy.types.Object, s: float):
        self.arm, self.s = arm, s
        self.bm = bmesh.new()
        self.materials: list[bpy.types.Material] = []
        self.bind: list[tuple[str, ...]] = []
        self.segments = {
            b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform
        }

    def _slot(self, mat) -> int:
        if mat not in self.materials:
            self.materials.append(mat)
        return self.materials.index(mat)

    def tube(self, rings, mat, bones, segments: int = 16) -> None:
        """rings: (centre, radius across X, radius across Y), in reference-height metres."""
        rows = []
        for centre, rx, ry in rings:
            c = Vector(centre) * self.s
            row = []
            for i in range(segments):
                a = 2 * math.pi * i / segments
                row.append(self.bm.verts.new(c + Vector((rx * math.cos(a), ry * math.sin(a), 0)) * self.s))
                self.bind.append(tuple(bones))
            rows.append(row)
        slot = self._slot(mat)
        for lower, upper in zip(rows, rows[1:]):
            for i in range(segments):
                k = (i + 1) % segments
                self.bm.faces.new((lower[i], lower[k], upper[k], upper[i])).material_index = slot
        for row in (rows[0], rows[-1][::-1]):
            self.bm.faces.new(row).material_index = slot

    def limb(self, a, b, ra, rb, mat, bones, steps: int = 5) -> None:
        """A tapered tube between two points, with its rings turned to follow the limb."""
        a, b = Vector(a), Vector(b)
        axis = (b - a).normalized()
        turn = Vector((0, 0, 1)).rotation_difference(axis)
        rows = []
        for n in range(steps + 1):
            f = n / steps
            bulge = 1 + 0.10 * math.sin(f * math.pi)
            radius = (ra + (rb - ra) * f) * bulge
            centre = (a + (b - a) * f) * self.s
            row = []
            for i in range(14):
                t = 2 * math.pi * i / 14
                offset = turn @ Vector((math.cos(t), math.sin(t), 0)) * radius * self.s
                row.append(self.bm.verts.new(centre + offset))
                self.bind.append(tuple(bones))
            rows.append(row)
        slot = self._slot(mat)
        for lower, upper in zip(rows, rows[1:]):
            for i in range(14):
                k = (i + 1) % 14
                self.bm.faces.new((lower[i], lower[k], upper[k], upper[i])).material_index = slot
        for row in (rows[0], rows[-1][::-1]):
            self.bm.faces.new(row).material_index = slot

    def ellipsoid(self, centre, radii, mat, bones, top_only: bool = False) -> None:
        rings = []
        count = 9
        start = 0.0 if top_only else -1.0
        for n in range(count):
            v = start + (1 - start) * (n + 0.02) / (count - 1 + 0.04)
            w = math.sqrt(max(1 - v * v, 0.0025))
            rings.append(((centre[0], centre[1], centre[2] + radii[2] * v), radii[0] * w, radii[1] * w))
        self.tube(rings, mat, bones, 20)

    def box(self, low, high, mat, bones) -> None:
        lx, ly, lz = (v * self.s for v in low)
        hx, hy, hz = (v * self.s for v in high)
        points = [(lx, ly, lz), (hx, ly, lz), (hx, hy, lz), (lx, hy, lz), (lx, ly, hz), (hx, ly, hz), (hx, hy, hz), (lx, hy, hz)]
        verts = [self.bm.verts.new(p) for p in points]
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
        blend = 0.07 * self.s
        share = max(0.0, 0.5 - (d2 - d1) / (2 * blend))
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
        for point, bones, vertex in zip(points, self.bind, range(len(points))):
            for bone, weight in self._weights(point, bones):
                group = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
                group.add([vertex], weight, "REPLACE")
        obj.parent = self.arm
        obj.modifiers.new("rig", "ARMATURE").object = self.arm
        return obj


def build_body(arm, player: str, s: float) -> None:
    p = PLAYERS[player]
    b = p["build"]
    shirt = material("shirt", p["shirt"], 0.55)
    trim = material("trim", p["trim"], 0.5)
    trousers = material("trousers", 0x172554, 0.7)
    skin = material("skin", p["skin"], 0.55)
    white = material("pads", 0xf1f5f9, 0.65)
    glove = material("gloves", 0xe2e8f0, 0.6)
    shoe = material("shoes", 0xf8fafc, 0.45)
    helmet = material("helmet", 0x1e3a8a, 0.3)
    grille = material("grille", 0x94a3b8, 0.3)
    willow = material("willow", 0xe9cf9b, 0.5)
    grip = material("grip", 0x1f2937, 0.8)

    body = MeshBuilder(arm, s)
    body.tube(
        [
            ((0, 0, 0.86), 0.150 * b, 0.115 * b), ((0, 0, 0.95), 0.170 * b, 0.128 * b),
            ((0, 0, 1.04), 0.150 * b, 0.112 * b),
        ],
        trousers, ("hips", "spine"),
    )
    body.tube(
        [
            ((0, 0, 1.00), 0.150 * b, 0.112 * b), ((0, 0, 1.12), 0.152 * b, 0.112 * b),
            ((0, 0, 1.26), 0.178 * b, 0.130 * b), ((0, 0, 1.38), 0.195 * b, 0.128 * b),
            ((0, 0, 1.45), 0.145 * b, 0.095 * b), ((0, 0, 1.48), 0.060, 0.058),
        ],
        shirt, ("hips", "spine", "chest", "neck"),
    )
    body.tube([((0, 0, 1.44), 0.078, 0.075), ((0, 0, 1.47), 0.072, 0.070)], trim, ("chest", "neck"))
    body.limb((0, 0, 1.44), (0, 0, 1.58), 0.054, 0.052, skin, ("neck", "head"))

    for side in "LR":
        m = lambda key: tuple(mirrored(JOINTS[key], side))
        arm_bones = (f"upper_arm_{side}", f"forearm_{side}")
        body.limb(m("shoulder"), m("elbow"), 0.058 * b, 0.046 * b, shirt, ("chest", *arm_bones))
        sleeve = Vector(m("shoulder")).lerp(Vector(m("elbow")), 0.72)
        body.limb(tuple(sleeve), tuple(Vector(m("shoulder")).lerp(Vector(m("elbow")), 0.78)), 0.051 * b, 0.050 * b, trim, arm_bones)
        body.limb(m("elbow"), m("wrist"), 0.043, 0.032, skin, arm_bones)
        wrist = Vector(m("wrist"))
        body.ellipsoid(tuple(wrist + Vector((0, 0, -0.025))), (0.048, 0.052, 0.068), glove, (f"hand_{side}",))
        body.limb(m("hip"), m("knee"), 0.088 * b, 0.060, trousers, ("hips", f"thigh_{side}", f"shin_{side}"))
        body.limb(m("knee"), m("ankle"), 0.057, 0.040, trousers, (f"thigh_{side}", f"shin_{side}"))
        # Batting pad: a raised front panel over the shin and knee.
        knee, ankle = Vector(m("knee")), Vector(m("ankle"))
        body.tube(
            [
                ((ankle.x, ankle.y - 0.030, 0.10), 0.066, 0.058),
                ((knee.x, -0.045, 0.34), 0.078, 0.070),
                ((knee.x, knee.y - 0.035, 0.53), 0.082, 0.072),
                ((knee.x, knee.y - 0.020, 0.64), 0.066, 0.054),
            ],
            white, (f"shin_{side}", f"thigh_{side}"),
        )
        toe = Vector(m("toe"))
        body.tube(
            [
                ((ankle.x, 0.055, 0.045), 0.040, 0.034),
                ((ankle.x, -0.020, 0.060), 0.052, 0.082),
                ((toe.x, toe.y + 0.045, 0.040), 0.050, 0.070),
            ],
            shoe, (f"foot_{side}",),
        )

    body.ellipsoid((0, 0.004, 1.645), (0.150, 0.158, 0.135), helmet, ("head",), top_only=True)
    body.box((-0.14, -0.175, 1.640), (0.14, -0.105, 1.650), helmet, ("head",))
    for z in (1.535, 1.575, 1.615):
        body.box((-0.105, -0.158, z), (0.105, -0.150, z + 0.008), grille, ("head",))
    for x in (-0.07, 0.0, 0.07):
        body.box((x - 0.004, -0.158, 1.525), (x + 0.004, -0.150, 1.645), grille, ("head",))

    # The bat is scaled back to real size so it stays 0.96 m on every player.
    g = Vector((0.02, -0.25, 0.90))
    k = 1 / s
    body.limb(tuple(g + Vector((0, 0, 0.03 * k))), tuple(g + Vector((0, 0, -0.25 * k))), 0.017 * k, 0.018 * k, grip, ("bat",))
    body.box(
        tuple(g + Vector((-0.028, -0.054, -0.84)) * k), tuple(g + Vector((0.028, 0.054, -0.25)) * k),
        willow, ("bat",),
    )
    body.finish("Body")

    # Kept separate so a FaceBuilder head can replace it without touching the body.
    head = MeshBuilder(arm, s)
    head.ellipsoid((0, -0.008, 1.625), (0.092, 0.112, 0.125), skin, ("head",))
    head.finish("Head")


def rest_rotation(pb) -> Quaternion:
    return pb.bone.matrix_local.to_quaternion()


def set_bone(pb, frame: int, world_rot: Quaternion | None = None, offset: Vector | None = None) -> None:
    pb.rotation_mode = "QUATERNION"
    rest = rest_rotation(pb)
    if world_rot is not None:
        pb.rotation_quaternion = rest.inverted() @ world_rot @ rest
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    if offset is not None:
        pb.location = rest.inverted() @ offset
        pb.keyframe_insert("location", frame=frame)


def turn(yaw: float = 0, lean: float = 0, side: float = 0) -> Quaternion:
    """Degrees. yaw: chest towards the bowler. lean: forward. side: towards the bowler."""
    z = Quaternion((0, 0, 1), math.radians(yaw))
    x = Quaternion((1, 0, 0), math.radians(lean))
    y = Quaternion((0, 1, 0), math.radians(side))
    return z @ y @ x


def stance(p: dict) -> dict:
    w = p["stance_width"]
    return {
        "hips": (0.0, -0.015, -p["crouch"]), "yaw": 14, "lean": 16, "chest": 6,
        "front": (0.11 + 0.09 * w, -0.01, 0.0, 10), "back": (-0.11 - 0.09 * w, 0.02, 0.0, -6),
        "grip": (0.03, -0.235, 0.895), "bat": (-0.12, -0.05, -1),
    }


def backlift(p: dict, extra: dict | None = None) -> dict:
    h = p["backlift"]
    pose = {
        **stance(p),
        "hips": (-0.025, -0.015, -p["crouch"]), "chest": 0, "yaw": 8,
        "grip": (-0.10 - 0.045 * h, -0.17, 0.97 + 0.17 * h),
        "bat": (-0.82, -0.04, -0.20 + 0.72 * h),
    }
    return {**pose, **(extra or {})}


def shot_keys(shot: str, p: dict) -> dict[int, dict]:
    base = stance(p)
    up = backlift(p)
    f = p["follow"]
    fw = lambda x, y=-0.04, yaw=24: (x, y, 0.0, yaw)
    if shot == "leave":
        lifted = {**up, "grip": (-0.03, -0.08, 1.40), "bat": (-0.42, 0.08, 0.90), "lean": 10}
        return {0: base, 6: up, 12: {**lifted, "front": fw(0.40), "hips": (0.10, -0.01, -0.09)}, 20: {**lifted, "front": fw(0.40), "hips": (0.10, -0.01, -0.08)}, 30: {**lifted, "front": fw(0.40), "hips": (0.08, -0.01, -0.07)}}
    if shot == "defend":
        hit = {**base, "hips": (0.17, -0.03, -0.14), "yaw": 26, "lean": 24, "chest": 8, "front": fw(0.56), "grip": (0.44, -0.28, 0.76), "bat": (-0.26, -0.03, -1)}
        return {0: base, 6: backlift(p, {"grip": (-0.03, -0.20, 1.02), "bat": (-0.55, -0.03, 0.10)}), 12: hit, 20: hit, 30: {**hit, "hips": (0.16, -0.03, -0.13)}}
    if shot == "work":
        hit = {**base, "hips": (0.06, 0.0, -0.09), "yaw": 34, "lean": 18, "chest": 20, "front": fw(0.34, 0.03, 30), "back": (-0.17, 0.05, 0.0, 12), "grip": (0.25, -0.22, 0.84), "bat": (0.08, 0.50, -0.86)}
        end = {**hit, "yaw": 48, "chest": 30, "grip": (0.12, 0.00, 0.99), "bat": (-0.36, 0.86, -0.30)}
        return {0: base, 6: up, 12: hit, 19: end, 30: {**end, "grip": (0.08, -0.02, 1.02)}}
    if shot == "drive":
        hit = {**base, "hips": (0.24, -0.03, -0.15), "yaw": 22, "lean": 26, "chest": 10, "front": fw(0.66), "back": (-0.16, 0.03, 0.0, 0), "grip": (0.40, -0.30, 0.74), "bat": (0.20, -0.10, -1)}
        through = {**hit, "yaw": 30, "chest": 16, "lean": 18, "grip": (0.52, -0.30, 0.86 + 0.36 * f), "bat": (0.72, -0.28, 0.62)}
        end = {**through, "yaw": 42, "chest": 24, "lean": 10, "grip": (0.26, -0.18, 1.08 + 0.36 * f), "bat": (-0.42, 0.20, 0.88)}
        return {0: base, 6: up, 12: hit, 17: through, 24: end, 30: end}
    if shot == "cut":
        planted = {**base, "hips": (-0.09, -0.11, -0.10), "yaw": 6, "lean": 20, "chest": 0, "front": (0.22, -0.02, 0.0, 16), "back": (-0.23, -0.30, 0.0, -28)}
        hit = {**planted, "grip": (0.08, -0.56, 1.06), "bat": (0.28, -0.84, -0.26)}
        end = {**planted, "yaw": -16, "chest": -12, "grip": (-0.14, -0.47, 1.19), "bat": (-0.84, -0.42, 0.14)}
        return {0: base, 6: {**up, "back": planted["back"], "hips": (-0.07, -0.08, -0.07)}, 12: hit, 19: end, 30: end}
    if shot == "pull":
        planted = {**base, "hips": (-0.10, 0.01, -0.08), "lean": 8, "yaw": 34, "chest": 22, "front": (0.27, 0.10, 0.0, 34), "back": (-0.24, -0.04, 0.0, 18)}
        hit = {**planted, "grip": (0.14, -0.20, 1.22), "bat": (0.74, 0.62, 0.12)}
        through = {**planted, "yaw": 62, "chest": 34, "grip": (-0.04, 0.20, 1.24), "bat": (-0.42, 0.86, 0.16)}
        end = {**through, "yaw": 74, "chest": 40, "grip": (-0.20, 0.10, 1.34), "bat": (-0.82, 0.28, 0.46)}
        return {0: base, 6: {**up, "hips": (-0.08, 0.0, -0.06)}, 12: hit, 18: through, 26: end, 30: end}
    if shot == "sweep":
        low = {**base, "hips": (0.14, -0.02, -0.43), "yaw": 26, "lean": 34, "chest": 12, "front": fw(0.58, -0.09, 20), "back": (-0.30, 0.09, 0.0, -18), "grip": (0.40, -0.13, 0.46), "bat": (0.62, 0.70, -0.24)}
        end = {**low, "yaw": 50, "chest": 26, "grip": (0.20, 0.22, 0.60), "bat": (-0.20, 0.95, 0.22)}
        return {0: base, 6: {**up, "hips": (0.05, -0.01, -0.22)}, 12: low, 20: end, 30: end}
    if shot == "loft":
        hit = {**base, "hips": (0.26, -0.03, -0.13), "yaw": 24, "lean": 18, "chest": 12, "front": fw(0.68), "back": (-0.14, 0.03, 0.0, 4), "grip": (0.36, -0.27, 0.84), "bat": (0.46, -0.10, -0.86)}
        through = {**hit, "yaw": 38, "chest": 22, "lean": 6, "grip": (0.55, -0.22, 1.42), "bat": (0.72, -0.10, 0.70)}
        end = {**through, "yaw": 56, "chest": 32, "lean": 0, "grip": (0.12, -0.06, 1.60), "bat": (-0.72, 0.10, 0.70)}
        high = backlift(p, {"grip": (-0.18, -0.13, 1.22), "bat": (-0.72, -0.02, 0.72)})
        return {0: base, 6: high, 12: hit, 17: through, 25: end, 30: end}
    raise ValueError(shot)


def key_pose(arm, frame: int, pose: dict, s: float) -> None:
    bones = arm.pose.bones
    hips = turn(pose["yaw"], pose["lean"] * 0.45)
    set_bone(bones["hips"], frame, hips, Vector(pose["hips"]) * s)
    # Spine bones are children, so each stores only its share of the bend and turn.
    share = turn(pose["chest"] * 0.5, pose["lean"] * 0.28)
    set_bone(bones["spine"], frame, share)
    set_bone(bones["chest"], frame, share)
    # The head counter-turns so the eyes stay level and on the bowler.
    total = pose["yaw"] + pose["chest"]
    set_bone(bones["neck"], frame, turn((min(82, 88 - total)) * 0.35, -pose["lean"] * 0.35))
    set_bone(bones["head"], frame, turn((min(82, 88 - total)) * 0.65, -pose["lean"] * 0.45))

    for side, key in (("L", "front"), ("R", "back")):
        x, y, z, foot_yaw = pose[key]
        ankle = mirrored(JOINTS["ankle"], side)
        target = Vector((x, y, ankle.z + z))
        set_bone(bones[f"foot_ik_{side}"], frame, turn(foot_yaw), (target - ankle) * s)

    rest_grip = Vector((0.02, -0.25, 0.90)) * s
    grip = Vector(pose["grip"]) * s
    direction = Vector(pose["bat"]).normalized()
    set_bone(bones["bat"], frame, Vector((0, 0, -1)).rotation_difference(direction), grip - rest_grip)


def fit_grip(arm, frame: int) -> None:
    """Move the bat at this key, keeping its angle, until both arms can reach the handle."""
    bones = arm.pose.bones
    bat = bones["bat"]
    rest = rest_rotation(bat)
    scene = bpy.context.scene
    for _ in range(12):
        scene.frame_set(frame)
        correction = Vector((0, 0, 0))
        for side in "LR":
            shoulder = bones[f"upper_arm_{side}"].head
            hand = bones[f"hand_ik_{side}"].head
            reach = (bones[f"upper_arm_{side}"].bone.length + bones[f"forearm_{side}"].bone.length) * 0.985
            gap = hand - shoulder
            if gap.length > reach:
                pull = -gap.normalized() * (gap.length - reach)
                if pull.length > correction.length:
                    correction = pull
        if correction.length < 1e-4:
            return
        bat.location = rest.inverted() @ ((rest @ bat.location) + correction)
        bat.keyframe_insert("location", frame=frame)


def make_clip(arm, name: str, keys: dict[int, dict], s: float) -> bpy.types.Action:
    arm.animation_data_create()
    arm.animation_data.action = None
    for frame, pose in keys.items():
        key_pose(arm, frame, pose, s)
    for frame in keys:
        fit_grip(arm, frame)
    action = arm.animation_data.action
    action.name = name
    action.use_fake_user = True
    arm.animation_data.action = None
    return action


def idle_keys(p: dict) -> dict[int, dict]:
    base = stance(p)
    settle = {**base, "hips": (base["hips"][0], base["hips"][1], base["hips"][2] - 0.012)}
    tap = {**settle, "grip": (0.035, -0.235, 0.915), "bat": (-0.10, -0.05, -1)}
    return {0: base, 10: settle, 15: tap, 20: settle, 30: base}


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
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    p = PLAYERS[player]
    s = p["height"] / REFERENCE_HEIGHT
    arm = build_armature(s)
    build_body(arm, player, s)
    make_clip(arm, "idle", idle_keys(p), s)
    for shot in ("leave", "defend", "work", "drive", "cut", "pull", "sweep", "loft"):
        make_clip(arm, shot, shot_keys(shot, p), s)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, LAST_FRAME
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    export(ASSETS / "characters" / f"{player}.glb", [arm, *meshes], False)
    export(ASSETS / "animations" / "scripted" / f"{player}.glb", [arm, *meshes], True)
    print(f"built {player}: {len(bpy.data.actions)} clips")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(PLAYERS)
    for name in args:
        build(name)
