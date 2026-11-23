"""Build rigged bowlers on the same MPFB pipeline as the batters, with one scripted delivery each.

Run from the repo root (no --factory-startup, which would disable MPFB):
  blender --background --python pipeline/build_bowler.py -- bumrah warne

Writes, outside git:
  ~/cricket-project/assets/characters/<player>.glb            body, kit, rig
  ~/cricket-project/assets/animations/scripted/<player>.glb   idle and <player>_delivery

Character space (Blender): the bowler starts at the origin and runs towards -Y, Z is up.
The clip carries the whole run-up, so planted feet do not slide. Clips are 30 fps.
Actions are stylised from docs/asset-pipeline.md, not motion capture of the real players.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_batter as bb  # noqa: E402

bb.PLAYERS.update({
    "bumrah": {
        "height": 1.78, "shirt": 0x1d4ed8, "trim": 0xf97316, "skin": 0x8f6242, "hair": 0x15110e,
        "macro": {"gender": 1.0, "age": 0.42, "muscle": 0.62, "weight": 0.40, "height": 0.58, "proportions": 0.62,
                  "race": {"asian": 0.85, "caucasian": 0.10, "african": 0.05}},
    },
    "warne": {
        "height": 1.83, "shirt": 0xeab308, "trim": 0x166534, "skin": 0xd9a98a, "hair": 0xd8bd7a,
        "macro": {"gender": 1.0, "age": 0.55, "muscle": 0.55, "weight": 0.60, "height": 0.64, "proportions": 0.55,
                  "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}},
    },
})

# Each foot contact is (frame, foot, distance run). Tracks are (frame, value) keys.
ACTIONS = {
    "bumrah": {
        "release": 51, "last": 78,
        # Short, stuttering approach: uneven steps, then a bound into a braced front leg.
        "contacts": [(0, "r", 0.0), (0, "l", 0.25), (7, "r", 1.25), (13, "l", 2.35), (18, "r", 3.05), (22, "l", 3.55),
                     (28, "r", 4.75), (34, "l", 6.0), (39, "r", 7.15), (45, "r", 8.35), (49, "l", 9.45),
                     (58, "r", 10.7), (66, "l", 11.55), (72, "r", 11.8)],
        "pelvis": [(0, 0.1), (13, 2.2), (22, 3.45), (34, 5.9), (45, 8.2), (49, 9.05), (51, 9.4), (58, 10.5), (66, 11.35), (78, 11.65)],
        "rise": [(0, 0.0), (39, -0.02), (42, 0.13), (45, -0.03), (49, -0.05), (51, 0.03), (58, -0.09), (78, -0.02)],
        # Very front-on chest at delivery.
        "yaw": [(0, 0), (39, -8), (45, -32), (49, -18), (51, -6), (58, 24), (78, 4)],
        "chest": [(0, 0), (45, -12), (51, 8), (58, 16), (78, 0)],
        "lean": [(0, 12), (39, 14), (45, 2), (49, -4), (51, 16), (56, 36), (66, 22), (78, 6)],
        # Near-straight bowling arm: hand relative to the pelvis as (side, forward, height).
        "right": [(0, (-0.27, 0.05, 0.02)), (39, (-0.28, 0.10, 0.08)), (43, (-0.30, -0.28, 0.20)), (46, (-0.34, -0.52, 0.30)),
                  (48, (-0.34, -0.40, 0.86)), (50, (-0.25, -0.10, 1.16)), (51, (-0.20, 0.12, 1.18)), (53, (-0.16, 0.55, 0.72)),
                  (56, (0.05, 0.52, 0.16)), (62, (0.18, 0.30, 0.02)), (78, (-0.26, 0.08, 0.02))],
        "left": [(0, (0.27, 0.05, 0.02)), (39, (0.28, 0.14, 0.12)), (44, (0.22, 0.38, 0.86)), (48, (0.20, 0.42, 0.92)),
                 (51, (0.34, 0.02, 0.28)), (56, (0.36, -0.22, 0.02)), (78, (0.26, 0.04, 0.02))],
        "flick": [(0, 0), (49, -42), (51, 8), (53, 58), (60, 12), (78, 0)],  # Late whip of the wrist.
        "spin": [(0, 0), (78, 0)],
    },
    "warne": {
        "release": 42, "last": 72,
        # Unhurried walk-in of a few paces.
        "contacts": [(0, "r", 0.0), (0, "l", 0.2), (9, "r", 0.85), (18, "l", 1.6), (27, "r", 2.3), (35, "r", 2.75), (40, "l", 3.55),
                     (52, "r", 4.3), (62, "l", 4.75)],
        "pelvis": [(0, 0.1), (18, 1.45), (27, 2.15), (35, 2.85), (40, 3.3), (42, 3.5), (52, 4.2), (62, 4.6), (72, 4.65)],
        "rise": [(0, 0.0), (27, -0.015), (32, 0.05), (35, -0.03), (40, -0.07), (42, -0.02), (52, -0.07), (72, -0.02)],
        # Side-on load, then a strong shoulder rotation through the ball.
        "yaw": [(0, -8), (27, -30), (35, -82), (40, -66), (42, -28), (47, 18), (56, 34), (72, 6)],
        "chest": [(0, 0), (35, -16), (40, -8), (42, 12), (48, 24), (72, 0)],
        "lean": [(0, 8), (35, 2), (40, -6), (42, 14), (48, 32), (58, 18), (72, 5)],
        "right": [(0, (-0.26, 0.10, 0.14)), (27, (-0.20, 0.16, 0.26)), (33, (-0.16, -0.10, 0.42)), (37, (-0.30, -0.40, 0.56)),
                  (40, (-0.30, -0.20, 0.96)), (41, (-0.24, -0.02, 1.05)), (42, (-0.18, 0.14, 1.05)), (44, (-0.10, 0.48, 0.72)),
                  (48, (0.14, 0.46, 0.14)), (56, (0.22, 0.24, 0.04)), (72, (-0.26, 0.08, 0.04))],
        "left": [(0, (0.26, 0.10, 0.12)), (27, (0.24, 0.16, 0.24)), (35, (0.16, 0.46, 0.84)), (39, (0.16, 0.48, 0.92)),
                 (42, (0.34, 0.04, 0.34)), (48, (0.38, -0.20, 0.04)), (72, (0.26, 0.04, 0.02))],
        "flick": [(0, 0), (38, -50), (41, -20), (43, 46), (50, 14), (72, 0)],
        "spin": [(0, 0), (38, -55), (41, -35), (43, 95), (50, 30), (72, 0)],  # Big leg-break wrist and fingers.
    },
}


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def track(keys, frame: float):
    """Smoothly interpolated value of a track, scalar or tuple."""
    if frame <= keys[0][0]:
        return keys[0][1]
    for (fa, a), (fb, b) in zip(keys, keys[1:]):
        if frame <= fb:
            t = smooth((frame - fa) / (fb - fa))
            return tuple(p + (q - p) * t for p, q in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * t
    return keys[-1][1]


def foot_at(contacts, side: str, frame: float) -> tuple[float, float]:
    """Distance along the run-up and lift of one foot: planted between contacts, arcing between them."""
    own = [(f, d) for f, s, d in contacts if s == side]
    if frame <= own[0][0]:
        return own[0][1], 0.0
    for (fa, da), (fb, db) in zip(own, own[1:]):
        if frame <= fb:
            # The foot leaves late and lands on its contact frame.
            start = fa + (fb - fa) * 0.25
            if frame <= start:
                return da, 0.0
            t = (frame - start) / (fb - start)
            return da + (db - da) * smooth(t), math.sin(math.pi * t) * min(0.16, 0.05 + abs(db - da) * 0.11)
    return own[-1][1], 0.0


def add_controls(arm) -> None:
    """Foot and hand targets, so the run-up can plant feet and place the bowling hand exactly."""
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bones = arm.data.edit_bones
    for side in "lr":
        for part in ("foot", "hand"):
            source = bones[f"{part}_{side}"]
            control = bones.new(f"{part}_ik_{side}")
            control.head, control.tail, control.roll = source.head, source.tail, source.roll
            control.use_deform = False
    if "Root" in bones:
        bones["Root"].use_deform = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for side in "lr":
        for bone, target in ((f"lowerarm_{side}", f"hand_ik_{side}"), (f"calf_{side}", f"foot_ik_{side}")):
            ik = arm.pose.bones[bone].constraints.new("IK")
            ik.target, ik.subtarget, ik.chain_count = arm, target, 2
        copy = arm.pose.bones[f"foot_{side}"].constraints.new("COPY_ROTATION")
        copy.target, copy.subtarget = arm, f"foot_ik_{side}"


def finish_kit(player: str, arm, head, eyes, s: float) -> None:
    """Bare hands for bowling, plus simple hair and eyes on the replaceable head."""
    bpy.data.materials["gloves"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = bb.rgb(bb.PLAYERS[player]["skin"])
    hair = bb.material("hair", bb.PLAYERS[player]["hair"], 0.8)
    white = bb.material("eye_white", 0xf4f1ea, 0.3)
    iris = bb.material("eye_iris", 0x1c120c, 0.25)
    gear = bb.MeshBuilder(arm)
    points = [Vector(v.co) for v in head.data.vertices]
    top = max(q.z for q in points)
    width = max(q.x for q in points) - min(q.x for q in points)
    front, back = min(q.y for q in points), max(q.y for q in points)
    eye_z = eyes[0].z if eyes[0] is not None else top - 0.115 * s
    centre = Vector((0, (front + back) / 2 + 0.012, eye_z + 0.035 * s))
    gear.dome(centre, (width / 2 + 0.006, (back - front) / 2 + 0.002, top - centre.z + 0.012), hair, ("head",), low=0.05)
    for eye in eyes:
        if eye is not None:
            gear.dome(eye - Vector((0, 0, 0.012 * s)), (0.0125 * s,) * 3, white, ("head",), low=-0.99)
            gear.dome(eye + Vector((0, -0.0105 * s, -0.005 * s)), (0.0055 * s, 0.003 * s, 0.0055 * s), iris, ("head",), low=-0.99)
    gear.finish("Gear")


def key_grip(arm, frame: int, spin: float) -> None:
    """Fingers round the ball. `spin` opens and rips them through release on the bowling hand."""
    bones = arm.pose.bones
    for side in "lr":
        fingers, _, palm = bb.hand_frame(arm, side)
        axis = fingers.cross(palm).normalized()
        curl = 34 if side == "r" else 48
        if side == "r":
            curl += spin * 0.25
        for finger, extra in zip(bb.FINGERS, (0, 3, 7, 12)):
            for joint, share in zip(("01", "02", "03"), (1.0, 1.1, 0.75)):
                bb.set_bone(bones[f"{finger}_{joint}_{side}"], frame, Quaternion(axis, math.radians((curl + extra) * share)))


def key_frame(arm, action: dict, frame: int, s: float, rest: dict) -> None:
    bones = arm.pose.bones
    run, rise = track(action["pelvis"], frame), track(action["rise"], frame)
    yaw, chest, lean = (track(action[k], frame) for k in ("yaw", "chest", "lean"))
    bb.set_bone(bones["pelvis"], frame, bb.turn(yaw, lean * 0.4), Vector((0, -run, rise * s)))
    share = bb.turn(chest / 3, lean * 0.2)
    for name in bb.SPINE:
        bb.set_bone(bones[name], frame, share)
    look = max(-75.0, min(75.0, -(yaw + chest)))  # Eyes stay on the target.
    bb.set_bone(bones["neck_01"], frame, bb.turn(look * 0.4, -lean * 0.3))
    bb.set_bone(bones["head"], frame, bb.turn(look * 0.6, -lean * 0.4))

    for side in "lr":
        distance, lift = foot_at(action["contacts"], side, frame)
        ankle = rest["foot", side]
        bb.set_bone(bones[f"foot_ik_{side}"], frame, bb.turn(0, -lift * 90), Vector((0, -distance, lift)))
        across, ahead, height = track(action["right" if side == "r" else "left"], frame)
        wanted = Vector((across * s, -(run + ahead * s), rest["pelvis"] + rise * s + height * s))
        bb.set_bone(bones[f"hand_ik_{side}"], frame, None, wanted - rest["hand", side])
        del ankle

    fingers, _, palm = bb.hand_frame(arm, "r")
    bb.set_bone(bones["hand_r"], frame, Quaternion(palm, math.radians(track(action["flick"], frame))) @
                Quaternion(fingers, math.radians(track(action["spin"], frame))))
    key_grip(arm, frame, track(action["spin"], frame))


def make_clip(arm, name: str, action: dict, s: float, rest: dict):
    arm.animation_data_create()
    arm.animation_data.action = None
    bb._last_rotation.clear()
    for frame in range(0, action["last"] + 1):
        key_frame(arm, action, frame, s, rest)
    clip = arm.animation_data.action
    clip.name = name
    clip.use_fake_user = True
    arm.animation_data.action = None
    return clip


def idle_action(action: dict) -> dict:
    """Standing at the top of the mark, breathing, with the same tracks as the delivery."""
    still = {key: [(0, track(action[key], 0)), (30, track(action[key], 0))] for key in ("pelvis", "yaw", "chest", "lean", "right", "left", "flick", "spin")}
    return {**still, "last": 30, "release": 0, "rise": [(0, 0.0), (15, -0.012), (30, 0.0)],
            "contacts": [(0, "r", 0.0), (0, "l", action["contacts"][1][2])]}


def report_release(arm, clip, frame: int) -> None:
    arm.animation_data.action = clip
    bpy.context.scene.frame_set(frame)
    hand = arm.pose.bones["hand_r"].head
    print(f"{clip.name}: release frame {frame} ({frame / bb.FPS:.2f} s), wrist at x={hand.x:.3f} run={-hand.y:.3f} height={hand.z:.3f}")
    arm.animation_data.action = None


def build(player: str) -> None:
    bb.clear_scene()
    scene = bpy.context.scene
    scene.render.fps = bb.FPS
    s = bb.PLAYERS[player]["height"] / bb.REFERENCE_HEIGHT
    body, arm, eyes = bb.make_human(player)
    add_controls(arm)
    head = bb.dress_body(body, arm, player)
    finish_kit(player, arm, head, eyes, s)
    data = arm.data.bones
    rest = {"pelvis": data["pelvis"].head_local.z}
    for side in "lr":
        rest["foot", side] = data[f"foot_{side}"].head_local.copy()
        rest["hand", side] = data[f"hand_{side}"].head_local.copy()
    action = ACTIONS[player]
    make_clip(arm, "idle", idle_action(action), s, rest)
    delivery = make_clip(arm, f"{player}_delivery", action, s, rest)
    report_release(arm, delivery, action["release"])
    scene.frame_start, scene.frame_end = 0, action["last"]
    scene.frame_set(0)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bb.export(bb.ASSETS / "characters" / f"{player}.glb", [arm, *meshes], False)
    bb.export(bb.ASSETS / "animations" / "scripted" / f"{player}.glb", [arm, *meshes], True)
    print(f"built {player}: {len(bpy.data.actions)} clips, {sum(len(m.data.polygons) for m in meshes)} faces")


if __name__ == "__main__":
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(ACTIONS)
    for name in names:
        build(name)
