"""Build a rigged fielder for each team on the same MPFB pipeline as the players.

Run from the repo root (no --factory-startup, which would disable MPFB):
  blender --background --python pipeline/build_fielder.py -- bumrah warne

Writes, outside git:
  ~/cricket-project/assets/animations/scripted/fielder_<bowler>.glb   body, kit, rig and clips

The fielders are generic people in the bowler's team colours, not real players.
Character space (Blender): the fielder faces -Y, Z is up. Clips are 30 fps and stay in place;
the game moves the fielder. Clip timings must match FIELD_CLIP in web/src/sim/hit.js:
  catch: hands meet the ball at frame 10 (0.333 s)
  field: picks the ball up at frame 6 (0.2 s) and releases the throw at frame 19 (0.633 s)
  run:   16-frame loop at 7 m/s, so the game can play it at its own running speed
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_batter as bb  # noqa: E402
import build_bowler as bw  # noqa: E402

RUN_SPEED = 7.0 / bb.FPS  # Metres per frame, the same as FIELDER_SPEED in hit.js.
RUN_FRAMES = 16

for team in ("bumrah", "warne"):
    kit = bb.PLAYERS[team]
    bb.PLAYERS[f"fielder_{team}"] = {
        "height": 1.78, "shirt": kit["shirt"], "trim": kit["trim"], "skin": 0xb07a55, "hair": 0x2a1d14,
        "macro": {"gender": 1.0, "age": 0.45, "muscle": 0.6, "weight": 0.5, "height": 0.58, "proportions": 0.6,
                  "race": {"asian": 0.4, "caucasian": 0.4, "african": 0.2}},
    }
    bw.HEAD_STYLES[f"fielder_{team}"] = {"hairline": 0.07, "volume": 0.012, "spikes": 0.006, "beard": False}


def lerp(a, b, t):
    return tuple(p + (q - p) * t for p, q in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * t


def keyed(keys: dict[int, dict], frame: float) -> dict:
    """The pose at `frame`, eased between the nearest keys."""
    frames = sorted(keys)
    if frame <= frames[0]:
        return keys[frames[0]]
    for fa, fb in zip(frames, frames[1:]):
        if frame <= fb:
            t = bw.smooth((frame - fa) / (fb - fa))
            return {k: lerp(keys[fa][k], keys[fb][k], t) for k in keys[fa]}
    return keys[frames[-1]]


# A pose: pelvis offset (x, y, z), body turn, feet (across, ahead, up, heel degrees) and hands
# (across, ahead, height), in metres from the ground under the fielder. +across is the left side.
READY = {
    "pelvis": (0.0, 0.0, -0.11), "yaw": 0.0, "lean": 22.0, "chest": 0.0, "curl": 30.0,
    "foot_l": (0.17, 0.02, 0.0, 0.0), "foot_r": (-0.17, 0.0, 0.0, 0.0),
    "hand_l": (0.12, 0.32, 0.78), "hand_r": (-0.12, 0.32, 0.78),
}
CROUCH = {
    **READY, "pelvis": (0.0, 0.04, -0.44), "lean": 34.0,
    "foot_l": (0.26, 0.0, 0.0, 12.0), "foot_r": (-0.26, 0.0, 0.0, 12.0),
    "hand_l": (0.07, 0.42, 0.42), "hand_r": (-0.07, 0.42, 0.42),
}


def idle_keys(base: dict) -> dict[int, dict]:
    breathe = {**base, "pelvis": (base["pelvis"][0], base["pelvis"][1], base["pelvis"][2] - 0.012)}
    return {0: base, 15: breathe, 30: base}


def run_pose(frame: float) -> dict:
    """One running cycle in place: each foot is down for 5 frames and slides back at run speed."""
    pose = {**READY, "pelvis": (0.0, 0.0, -0.07), "lean": 14.0, "chest": 0.0, "curl": 55.0}
    for side, offset, across in (("l", 0, 0.11), ("r", RUN_FRAMES / 2, -0.11)):
        u = ((frame - offset) % RUN_FRAMES) / RUN_FRAMES
        down = 5 / RUN_FRAMES
        reach = RUN_SPEED * 5 / 2  # Half the ground contact length.
        if u < down:
            ahead, up, heel = reach - 2 * reach * (u / down), 0.0, 30 * bw.smooth((u / down - 0.6) / 0.4)
        else:
            t = (u - down) / (1 - down)
            ahead = -reach + 2 * reach * bw.smooth(min(max((t - 0.12) / 0.88, 0), 1))
            up = 0.36 * math.sin(math.pi * t ** 0.75)
            heel = 45 * math.sin(math.pi * min(t / 0.75, 1))
        pose[f"foot_{side}"] = (across, ahead, up, heel)
        # The opposite arm swings with each leg, elbows bent.
        swing = math.cos(2 * math.pi * u)
        pose[f"hand_{'r' if side == 'l' else 'l'}"] = (-across * 2.2, 0.08 + 0.28 * swing, 1.0 + 0.12 * swing)
    u = (frame % (RUN_FRAMES / 2)) / (RUN_FRAMES / 2)
    pose["pelvis"] = (0.0, 0.0, -0.07 - 0.03 * math.cos(2 * math.pi * (u - 0.1)))
    return pose


def catch_keys() -> dict[int, dict]:
    reach = {**READY, "pelvis": (0.0, 0.0, -0.08), "lean": 10.0, "curl": 22.0,
             "hand_l": (0.06, 0.46, 1.3), "hand_r": (-0.06, 0.46, 1.3)}
    held = {**reach, "lean": 16.0, "curl": 72.0, "hand_l": (0.06, 0.24, 1.2), "hand_r": (-0.06, 0.24, 1.2)}
    return {0: READY, 10: reach, 18: held, 30: {**held, "lean": 8.0}}


def field_keys() -> dict[int, dict]:
    """Run in, scoop the ball, turn side-on and throw overarm."""
    scoop = {**READY, "pelvis": (0.0, 0.08, -0.34), "lean": 52.0, "curl": 40.0,
             "foot_l": (0.2, 0.3, 0.0, 10.0), "foot_r": (-0.2, -0.1, 0.0, 30.0),
             "hand_l": (0.1, 0.5, 0.1), "hand_r": (-0.04, 0.5, 0.06)}
    gather = {**scoop, "pelvis": (0.0, 0.0, -0.1), "lean": 10.0, "yaw": -50.0, "curl": 60.0,
              "hand_l": (0.15, 0.3, 1.1), "hand_r": (-0.1, 0.2, 1.15)}
    cocked = {**gather, "yaw": -70.0, "chest": -10.0, "lean": 0.0, "foot_l": (0.2, 0.55, 0.0, 0.0),
              "hand_l": (0.3, 0.55, 1.45), "hand_r": (-0.35, -0.45, 1.65)}
    release = {**cocked, "yaw": 10.0, "chest": 20.0, "lean": 22.0, "foot_r": (-0.2, -0.1, 0.0, 45.0),
               "hand_l": (0.32, -0.1, 1.0), "hand_r": (-0.12, 0.5, 1.8), "curl": 10.0}
    finish = {**release, "yaw": 30.0, "chest": 26.0, "lean": 32.0, "hand_l": (0.3, -0.2, 0.9), "hand_r": (0.2, 0.42, 0.85)}
    return {0: READY, 6: scoop, 11: gather, 16: cocked, 19: release, 24: finish, 30: finish}


def key_frame(arm, pose: dict, frame: int, s: float, rest: dict) -> None:
    bones = arm.pose.bones
    px, py, pz = pose["pelvis"]
    bb.set_bone(bones["pelvis"], frame, bb.turn(pose["yaw"], pose["lean"] * 0.4), Vector((px, -py, pz)) * s)
    share = bb.turn(pose["chest"] / 3, pose["lean"] * 0.2)
    for name in bb.SPINE:
        bb.set_bone(bones[name], frame, share)
    look = max(-70.0, min(70.0, -(pose["yaw"] + pose["chest"])))  # Eyes stay on the ball.
    bb.set_bone(bones["neck_01"], frame, bb.turn(look * 0.4, -pose["lean"] * 0.3))
    bb.set_bone(bones["head"], frame, bb.turn(look * 0.6, -pose["lean"] * 0.4))
    for side in "lr":
        across, ahead, up, heel = pose[f"foot_{side}"]
        ankle = Vector((across * s, -ahead * s, rest["foot", side].z + up))
        bb.place_foot(arm, side, frame, ankle, 0.0, heel)
        hx, hy, hz = pose[f"hand_{side}"]
        bb.set_bone(bones[f"hand_ik_{side}"], frame, None, Vector((hx * s, -hy * s, hz * s)) - rest["hand", side])
    curl(arm, frame, pose["curl"])


def curl(arm, frame: int, degrees: float) -> None:
    """Fingers from open (0) to a closed fist (about 80)."""
    bones = arm.pose.bones
    for side in "lr":
        fingers, _, palm = bb.hand_frame(arm, side)
        axis = fingers.cross(palm).normalized()
        for finger in bb.FINGERS:
            for joint, share in zip(("01", "02", "03"), (1.0, 1.1, 0.75)):
                bb.set_bone(bones[f"{finger}_{joint}_{side}"], frame, Quaternion(axis, math.radians(degrees * share)))


def make_clip(arm, name: str, pose_at, last: int, s: float, rest: dict):
    arm.animation_data_create()
    arm.animation_data.action = None
    bb._last_rotation.clear()
    for frame in range(last + 1):
        key_frame(arm, pose_at(frame), frame, s, rest)
    clip = arm.animation_data.action
    clip.name = name
    clip.use_fake_user = True
    arm.animation_data.action = None
    return clip


def build(team: str) -> None:
    import bpy

    player = f"fielder_{team}"
    bb.clear_scene()
    scene = bpy.context.scene
    scene.render.fps = bb.FPS
    s = bb.PLAYERS[player]["height"] / bb.REFERENCE_HEIGHT
    body, arm, eyes = bb.make_human(player)
    bw.add_controls(arm)
    bb.add_knee_poles(arm)
    head = bb.dress_body(body, arm, player)
    bw.finish_kit(player, arm, head, eyes, s)
    data = arm.data.bones
    rest = {}
    for side in "lr":
        rest["foot", side] = data[f"foot_{side}"].head_local.copy()
        rest["hand", side] = data[f"hand_{side}"].head_local.copy()
    make_clip(arm, "idle", lambda f: keyed(idle_keys(READY), f), 30, s, rest)
    make_clip(arm, "crouch", lambda f: keyed(idle_keys(CROUCH), f), 30, s, rest)
    make_clip(arm, "run", run_pose, RUN_FRAMES, s, rest)
    make_clip(arm, "catch", lambda f: keyed(catch_keys(), f), 30, s, rest)
    make_clip(arm, "field", lambda f: keyed(field_keys(), f), 30, s, rest)
    scene.frame_start, scene.frame_end = 0, 30
    scene.frame_set(0)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bb.export(bb.ASSETS / "animations" / "scripted" / f"{player}.glb", [arm, *meshes], True)
    print(f"built {player}: {len(bpy.data.actions)} clips, {sum(len(m.data.polygons) for m in meshes)} faces")


if __name__ == "__main__":
    teams = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["bumrah", "warne"]
    for name in teams:
        build(name)
