// Players. Batters are rigged glTF characters when their files exist in the local assets
// folder, otherwise capsules. Bowlers are capsules until Turn 6. The API stays small:
// root, setRunUp(f), setSwing(shot, f), reset(), update(dt).
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { closestToBlade } from "../sim/ball.js";
import { plantedFoot } from "../shots.js";
import { moveWorld, reachFraction, reachTo, rotateWorld } from "./ik.js";

// Every swing clip lasts SWING.time seconds and meets the ball SWING.lead seconds in.
export const SWING = { lead: 0.4, time: 1.0 };
const MAX_BAT_ADJUST = 0.55; // Metres the hands may move from the clip to meet the ball.
const MAX_SHUFFLE = 0.24; // Metres the batter may shuffle across the crease to the line.
const MAX_WRIST_TURN = THREE.MathUtils.degToRad(48); // How far the wrists may turn the bat.
const BLADE = [0.36, 0.86]; // Hitting part of the bat, in metres from the top of the handle.
const RECOVER_SECONDS = 0.3;
const smooth = (x) => {
  const t = Math.min(Math.max(x, 0), 1);
  return t * t * (3 - 2 * t);
};

export const KIT = {
  tendulkar: { name: "TENDULKAR", number: 10, shirt: 0x1d4ed8, trim: 0xf59e0b, height: 1.65 },
  kohli: { name: "KOHLI", number: 18, shirt: 0x1e40af, trim: 0xf97316, height: 1.75 },
  bumrah: { name: "BUMRAH", number: 93, shirt: 0x1d4ed8, trim: 0xf97316, height: 1.78 },
  warne: { name: "WARNE", number: 23, shirt: 0xeab308, trim: 0x166534, height: 1.83 },
};

// Bat swing per shot: start and end rotation about the batter's hands (radians).
const SWINGS = {
  leave: [0.2, -1.5], defend: [0.5, 0.05], work: [0.9, -0.9], drive: [1.7, -1.1],
  cut: [1.4, -0.3], pull: [1.6, -1.9], sweep: [1.2, -1.5], loft: [2.2, -2.3],
};

function backPrint({ name, number }) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.font = "bold 34px sans-serif";
  ctx.fillText(name, 128, 54);
  ctx.font = "bold 150px sans-serif";
  ctx.fillText(String(number), 128, 200);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Mesh(new THREE.PlaneGeometry(0.36, 0.36), new THREE.MeshBasicMaterial({ map: texture, transparent: true }));
}

function capsuleBody(kit) {
  const root = new THREE.Group();
  const scale = kit.height / 1.75;
  const shirt = new THREE.MeshStandardMaterial({ color: kit.shirt, roughness: 0.55 });
  const trousers = new THREE.MeshStandardMaterial({ color: 0x172554, roughness: 0.7 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xc99a76, roughness: 0.6 });

  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, 0.44, 6, 16), shirt);
  torso.position.y = 1.12;
  const hips = new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.52, 6, 16), trousers);
  hips.position.y = 0.46;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.125, 20, 16), skin);
  head.position.y = 1.61;
  for (const mesh of [torso, hips, head]) {
    mesh.castShadow = true;
    root.add(mesh);
  }
  const print = backPrint(kit);
  print.position.set(0, 1.18, 0.205);
  root.add(print);
  root.scale.setScalar(scale);
  return { root, head, shirt };
}

/** A rigged batter from /player-assets, or null if its files are not available. */
async function loadRiggedBatter(id, source) {
  const loader = new GLTFLoader();
  let character, motion;
  try {
    [character, motion] = await Promise.all([
      loader.loadAsync(`/player-assets/characters/${id}.glb`),
      loader.loadAsync(`/player-assets/animations/${source}/${id}.glb`),
    ]);
  } catch {
    return null;
  }

  const root = new THREE.Group();
  const model = character.scene;
  model.traverse((node) => {
    if (node.isMesh) {
      node.castShadow = true;
      node.frustumCulled = false;
    }
  });
  root.add(model);
  root.position.set(0.3, 0, -8.98);
  root.rotation.y = -Math.PI / 2;
  root.updateMatrixWorld(true);

  const chest = model.getObjectByName("spine_03");
  if (chest) {
    const print = backPrint(KIT[id]);
    print.scale.setScalar(0.8);
    print.position.set(0, 1.24 * (KIT[id].height / 1.75), -0.16);
    print.rotation.y = Math.PI;
    root.add(print);
    root.updateMatrixWorld(true);
    chest.attach(print);
  }

  const mixer = new THREE.AnimationMixer(model);
  const actions = Object.fromEntries(motion.animations.map((clip) => [clip.name, mixer.clipAction(clip)]));
  const idle = actions.idle;
  const bat = model.getObjectByName("bat");
  const sweet = model.getObjectByName("bat_sweet");
  const arms = ["l", "r"].map((side) => {
    const [upper, lower, hand] = ["upperarm", "lowerarm", "hand"].map((n) => model.getObjectByName(`${n}_${side}`));
    return { upper, lower, hand };
  });
  const legs = Object.fromEntries(["l", "r"].map((side) => {
    const [upper, lower, foot] = ["thigh", "calf", "foot"].map((n) => model.getObjectByName(`${n}_${side}`));
    return [side, { upper, lower, foot }];
  }));
  const footAt = new THREE.Vector3();
  const slip = new THREE.Vector3();
  const shoulder = new THREE.Vector3();
  const wrist = new THREE.Vector3();
  const elbow = new THREE.Vector3();
  const move = new THREE.Vector3();
  const top = new THREE.Vector3();
  const tip = new THREE.Vector3();
  const along = new THREE.Vector3();
  const toBall = new THREE.Vector3();
  const aimBall = new THREE.Vector3();
  const full = new THREE.Quaternion();
  const pivot = new THREE.Quaternion();
  const reachOf = (arm) => {
    arm.upper.getWorldPosition(shoulder);
    arm.lower.getWorldPosition(elbow);
    arm.hand.getWorldPosition(wrist);
    return (shoulder.distanceTo(elbow) + elbow.distanceTo(wrist)) * 0.995;
  };

  // Where each shot's sweet spot is at contact, before any adjustment to the ball.
  idle.play();
  const contacts = {};
  for (const [name, action] of Object.entries(actions)) {
    if (action === idle) continue;
    idle.setEffectiveWeight(0);
    action.play();
    action.paused = true;
    action.time = SWING.lead;
    action.setEffectiveWeight(1);
    mixer.update(0);
    model.updateMatrixWorld(true);
    const top = bat.getWorldPosition(new THREE.Vector3());
    const along = sweet.getWorldPosition(new THREE.Vector3()).sub(top).normalize();
    contacts[name] = BLADE.map((d) => top.clone().addScaledVector(along, d));
    action.stop();
  }
  idle.setEffectiveWeight(1);
  mixer.update(0);

  let swing = null;
  let recover = 0;
  let aimOffset = null;
  let shuffle = 0;
  let shuffleNow = 0;
  const homeX = root.position.x;
  const setShuffle = (x) => {
    shuffleNow = x;
    root.position.x = homeX + x;
    root.updateMatrixWorld(true);
  };

  /** The body shuffles across the crease, but the planted foot stays where it is on the ground. */
  function lockFoot(clip) {
    if (!shuffleNow) return;
    const leg = legs[plantedFoot(clip)];
    model.updateMatrixWorld(true);
    leg.foot.getWorldPosition(footAt);
    footAt.x -= shuffleNow;
    reachTo(leg.upper, leg.lower, leg.foot, footAt);
  }

  function applyAim(f, clip) {
    setShuffle(shuffle * smooth(f / (SWING.lead / SWING.time)));
    lockFoot(clip);
    if (!aimOffset) return;
    const strength = smooth((f - 0.08) / (SWING.lead / SWING.time - 0.08)) * (1 - smooth((f - 0.46) / 0.26));
    if (strength <= 0) return;
    model.updateMatrixWorld(true);
    move.copy(aimOffset).multiplyScalar(strength);
    let fraction = 1;
    for (const arm of arms) {
      const reach = reachOf(arm);
      fraction = Math.min(fraction, reachFraction(shoulder, wrist, move, reach));
    }
    move.multiplyScalar(fraction);

    // Whatever the hands cannot cover, the wrists cover by turning the bat towards the ball.
    bat.getWorldPosition(top).add(move);
    along.copy(sweet.getWorldPosition(tip)).sub(bat.getWorldPosition(wrist)).normalize();
    toBall.copy(aimBall).sub(top).normalize();
    full.setFromUnitVectors(along, toBall);
    const angle = 2 * Math.acos(Math.min(Math.abs(full.w), 1));
    const limit = angle > MAX_WRIST_TURN ? MAX_WRIST_TURN / angle : 1;
    pivot.identity().slerp(full, limit * strength);

    const targets = arms.map((arm) => arm.hand.getWorldPosition(new THREE.Vector3()).add(move).sub(top).applyQuaternion(pivot).add(top));
    moveWorld(bat, move);
    rotateWorld(bat, pivot);
    arms.forEach((arm, i) => reachTo(arm.upper, arm.lower, arm.hand, targets[i]));

    // If an arm could not stretch far enough, bring the bat back so both hands stay on it.
    slip.set(0, 0, 0);
    arms.forEach((arm, i) => {
      arm.hand.getWorldPosition(wrist).sub(targets[i]);
      if (wrist.lengthSq() > slip.lengthSq()) slip.copy(wrist);
    });
    if (slip.lengthSq() > 1e-8) {
      moveWorld(bat, slip);
      arms.forEach((arm, i) => reachTo(arm.upper, arm.lower, arm.hand, targets[i].add(slip)));
    }
    arms.forEach((arm) => rotateWorld(arm.hand, pivot));
  }

  return {
    root,
    rigged: true,
    /**
     * Steer this swing to the ball on `points`, using footwork first and then the hands.
     * Returns where and when the ball is met, or null if this shot has no contact pose.
     */
    planContact(shot, points) {
      const blade = contacts[shot];
      const plan = blade && closestToBlade(points, blade[0], blade[1]);
      if (!plan) return null;
      const { ball, blade: spot } = plan;
      shuffle = THREE.MathUtils.clamp(ball.x - spot.x, -MAX_SHUFFLE, MAX_SHUFFLE);
      aimBall.set(ball.x, ball.y, ball.z);
      aimOffset = new THREE.Vector3(ball.x - spot.x - shuffle, ball.y - spot.y, ball.z - spot.z);
      if (aimOffset.length() > MAX_BAT_ADJUST) aimOffset.setLength(MAX_BAT_ADJUST);
      return ball;
    },
    /** Play the next swing with no steering, for shots that miss. */
    clearAim() {
      aimOffset = null;
      shuffle = 0;
    },
    reset() {
      aimOffset = null;
      shuffle = 0;
      idle.paused = false;
      idle.setLoop(THREE.LoopRepeat);
      if (!idle.isRunning()) idle.play();
      if (swing) recover = RECOVER_SECONDS;
      else idle.setEffectiveWeight(1);
      mixer.update(0);
    },
    setSwing(shot, f) {
      const action = actions[shot] ?? actions.defend;
      if (swing !== action) {
        swing?.stop();
        swing = action;
        action.play();
      }
      recover = 0;
      action.paused = true;
      action.time = Math.min(f, 0.999) * action.getClip().duration;
      const weight = smooth(f / 0.12);
      action.setEffectiveWeight(weight);
      idle.setEffectiveWeight(1 - weight);
      mixer.update(0);
      applyAim(f, shot);
    },
    update(dt) {
      if (recover > 0) {
        recover -= dt;
        const weight = smooth(Math.max(recover, 0) / RECOVER_SECONDS);
        swing.setEffectiveWeight(weight);
        idle.setEffectiveWeight(1 - weight);
        setShuffle(shuffleNow * (recover > 0 ? 1 - Math.min(dt / recover, 1) : 0));
        if (recover <= 0) {
          swing.stop();
          swing = null;
        }
        mixer.update(dt);
      } else if (!swing) {
        mixer.update(dt);
      }
    },
  };
}

/** The rigged batter if available, otherwise the capsule. `source` picks the animation folder. */
export async function createBatter(id, source = "scripted") {
  const rigged = await loadRiggedBatter(id, source);
  if (rigged) return rigged;
  console.info(`No rigged character for ${id}, using the capsule.`);
  return createCapsuleBatter(id);
}

function createCapsuleBatter(id) {
  const kit = KIT[id];
  const { root, head } = capsuleBody(kit);
  const helmet = new THREE.Mesh(
    new THREE.SphereGeometry(0.145, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.62),
    new THREE.MeshStandardMaterial({ color: 0x1e3a8a, roughness: 0.35 }),
  );
  helmet.position.copy(head.position).setY(head.position.y + 0.015);
  helmet.castShadow = true;
  root.add(helmet);

  const pivot = new THREE.Group();
  pivot.position.set(0, 1.02, -0.24);
  const willow = new THREE.MeshStandardMaterial({ color: 0xe9cf9b, roughness: 0.5 });
  const blade = new THREE.Mesh(new THREE.BoxGeometry(0.105, 0.56, 0.05), willow);
  blade.position.y = -0.56;
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.017, 0.017, 0.3, 8), new THREE.MeshStandardMaterial({ color: 0x1f2937 }));
  handle.position.y = -0.14;
  blade.castShadow = true;
  pivot.add(blade, handle);
  root.add(pivot);

  // Right-hander on strike, chest towards off side (-x), just outside leg stump.
  root.position.set(0.3, 0, -8.98);
  root.rotation.y = -Math.PI / 2;

  return {
    root,
    reset() { pivot.rotation.set(0, 0, 0.12); },
    update() {},
    planContact: () => null,
    clearAim() {},
    setSwing(shot, f) {
      const [from, to] = SWINGS[shot.split("_")[0]] ?? SWINGS.defend;
      const windUp = Math.min(f / 0.45, 1);
      const through = Math.max((f - 0.45) / 0.55, 0);
      pivot.rotation.z = 0.12 + (from - 0.12) * windUp + (to - from) * through * through * (3 - 2 * through);
    },
  };
}

export function createBowler(id) {
  const kit = KIT[id];
  const { root } = capsuleBody(kit);
  const arm = new THREE.Group();
  arm.position.set(0.25, 1.36, 0);
  const limb = new THREE.Mesh(new THREE.CapsuleGeometry(0.052, 0.58, 4, 10), new THREE.MeshStandardMaterial({ color: 0xc99a76, roughness: 0.6 }));
  limb.position.y = 0.31;
  limb.castShadow = true;
  arm.add(limb);
  root.add(arm);

  // Bumrah's real run-up is short for a quick; Warne walks in a few paces.
  const runUp = id === "bumrah" ? 9.5 : 3.2;
  const start = new THREE.Vector3(-0.72, 0, 9.1 + runUp);
  const end = new THREE.Vector3(-0.42, 0, 9.1);
  root.position.copy(start);

  return {
    root,
    reset() { root.position.copy(start); arm.rotation.x = Math.PI; },
    /** f runs 0 to 1 over the run-up. Arm comes over at the end. */
    setRunUp(f) {
      root.position.lerpVectors(start, end, f);
      root.position.y = Math.abs(Math.sin(f * Math.PI * (id === "bumrah" ? 9 : 4))) * (id === "bumrah" ? 0.07 : 0.025);
      const bowl = Math.max((f - 0.82) / 0.18, 0);
      arm.rotation.x = Math.PI - bowl * Math.PI * 1.3;
    },
    followThrough(f) {
      root.position.z = end.z - f * (id === "bumrah" ? 3 : 1.2);
      root.position.y = 0;
    },
  };
}
