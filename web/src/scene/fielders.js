// The fielding side. Rigged fielders in the bowler's team colours when their file exists in the
// local assets folder (pipeline/build_fielder.py), otherwise simple jointed figures. Positions and
// clips come from fielderStates in sim/hit.js, so a live ball and its replay always look the same.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { clone } from "three/addons/utils/SkeletonUtils.js";
import { FIELDS, fielderStates, handWindow, heldBy } from "../sim/hit.js";
import { reachTo } from "./ik.js";

const STRIDE_RATE = 11; // Radians of leg swing per second while running (fallback figures).
const LOOPS = new Set(["idle", "crouch", "run"]);
const smooth = (x) => {
  const t = Math.min(Math.max(x, 0), 1);
  return t * t * (3 - 2 * t);
};

function figure(shirt, trousers, skin, keeper) {
  const root = new THREE.Group();
  const part = (geometry, material, x, y, parent = root) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, 0);
    mesh.castShadow = true;
    parent.add(mesh);
    return mesh;
  };
  const limb = (x, y, material, length, radius) => {
    const pivot = new THREE.Group();
    pivot.position.set(x, y, 0);
    root.add(pivot);
    part(new THREE.CapsuleGeometry(radius, length, 3, 8), material, 0, -length / 2 - radius, pivot);
    return pivot;
  };
  part(new THREE.CapsuleGeometry(0.18, 0.42, 4, 10), shirt, 0, 1.18);
  part(new THREE.SphereGeometry(0.115, 14, 10), skin, 0, 1.68);
  const legs = [limb(-0.11, 0.88, trousers, 0.68, 0.1), limb(0.11, 0.88, trousers, 0.68, 0.1)];
  const arms = [limb(-0.26, 1.42, shirt, 0.5, 0.068), limb(0.26, 1.42, shirt, 0.5, 0.068)];
  if (keeper) {
    const gloves = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.5 });
    for (const arm of arms) part(new THREE.SphereGeometry(0.075, 10, 8), gloves, 0, -0.66, arm);
  }
  return { root, legs, arms };
}

function simpleFielders(scene, field, kit) {
  const shirt = new THREE.MeshStandardMaterial({ color: kit.shirt, roughness: 0.6 });
  const trousers = new THREE.MeshStandardMaterial({ color: 0x172554, roughness: 0.7 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xc99a76, roughness: 0.6 });
  const figures = field.map((_, i) => figure(shirt, trousers, skin, i === 0));
  for (const f of figures) scene.add(f.root);
  return {
    rigged: false,
    pose(hit, after, ballAt) {
      fielderStates(hit, field, after, ballAt).forEach((state, i) => {
        const { root, legs, arms } = figures[i];
        root.position.set(state.x, 0, state.z);
        root.rotation.y = state.heading;
        const swing = state.running ? Math.sin(after * STRIDE_RATE) * 0.85 : 0;
        legs[0].rotation.x = swing;
        legs[1].rotation.x = -swing;
        arms[0].rotation.x = -swing;
        arms[1].rotation.x = swing;
        if (state.action === "catch") {
          arms[0].rotation.x = -2.5;
          arms[1].rotation.x = -2.5;
        } else if (state.action === "throw") {
          arms[1].rotation.x = -2.8;
        }
      });
      return null;
    },
  };
}

/** A palm point: just past the wrist, towards the middle knuckle. */
function palm(hand, knuckle, out) {
  hand.getWorldPosition(out);
  return out.lerp(knuckle.getWorldPosition(new THREE.Vector3()), 0.75);
}

function riggedFielders(scene, field, gltf) {
  const clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
  const people = field.map((_, i) => {
    const model = clone(gltf.scene);
    model.traverse((node) => {
      if (!node.isMesh) return;
      node.castShadow = true;
      node.frustumCulled = false;
      // The keeper wears white gloves.
      if (i === 0 && node.material?.name === "gloves") {
        node.material = node.material.clone();
        node.material.color.set(0xf1f5f9);
      }
    });
    const root = new THREE.Group();
    root.add(model);
    scene.add(root);
    const mixer = new THREE.AnimationMixer(model);
    const actions = Object.fromEntries(Object.entries(clips).map(([name, clip]) => [name, mixer.clipAction(clip)]));
    const bone = (name) => model.getObjectByName(name);
    const arms = Object.fromEntries(["l", "r"].map((s) => [s, {
      upper: bone(`upperarm_${s}`), lower: bone(`lowerarm_${s}`), hand: bone(`hand_${s}`), knuckle: bone(`middle_01_${s}`),
    }]));
    return { root, mixer, actions, arms, playing: null };
  });

  const side = new THREE.Vector3();
  const towards = new THREE.Vector3();
  const target = new THREE.Vector3();
  const wrist = new THREE.Vector3();
  const held = new THREE.Vector3();
  const ball = new THREE.Vector3();

  function play(person, name, time) {
    const action = person.actions[name] ?? person.actions.idle;
    if (person.playing !== action) {
      person.playing?.stop();
      person.playing = action;
      action.play();
    }
    action.paused = true;
    const duration = action.getClip().duration;
    action.time = LOOPS.has(name) ? ((time % duration) + duration) % duration : Math.min(Math.max(time, 0), duration - 1e-3);
    action.setEffectiveWeight(1);
    person.mixer.update(0);
  }

  /** Pull one hand's palm towards `point` by `weight`, using the arm's own two-bone chain. */
  function reach(person, s, point, weight) {
    const arm = person.arms[s];
    if (!arm.upper || weight <= 0) return;
    palm(arm.hand, arm.knuckle, held);
    arm.hand.getWorldPosition(wrist);
    // Move the wrist by the same amount the palm needs to move.
    target.copy(point).sub(held).multiplyScalar(weight).add(wrist);
    reachTo(arm.upper, arm.lower, arm.hand, target);
  }

  return {
    rigged: true,
    pose(hit, after, ballAt) {
      const states = fielderStates(hit, field, after, ballAt);
      states.forEach((state, i) => {
        const person = people[i];
        person.root.position.set(state.x, 0, state.z);
        person.root.rotation.y = state.heading;
        person.root.updateMatrixWorld(true);
        play(person, state.clip, state.clipTime);
      });
      if (!hit || hit.fielder === null || !ballAt) return null;
      const person = people[hit.fielder];
      ball.set(ballAt.x, ballAt.y, ballAt.z);
      const window = handWindow(hit);
      if (window) {
        const [start, full, end] = window;
        const weight = after < full ? smooth((after - start) / (full - start)) : 1 - smooth((after - full) / (end - full));
        if (hit.action === "catch") {
          // Two hands either side of the ball, cupped round it.
          side.set(1, 0, 0).applyQuaternion(person.root.quaternion);
          towards.set(0, 0, 1).applyQuaternion(person.root.quaternion);
          reach(person, "l", ball.clone().addScaledVector(side, 0.055).addScaledVector(towards, -0.03), weight);
          reach(person, "r", ball.clone().addScaledVector(side, -0.055).addScaledVector(towards, -0.03), weight);
        } else {
          reach(person, "r", ball, weight);
        }
      }
      const holding = heldBy(hit, after);
      if (!holding) return null;
      if (holding === "both") {
        const l = palm(person.arms.l.hand, person.arms.l.knuckle, new THREE.Vector3());
        return palm(person.arms.r.hand, person.arms.r.knuckle, new THREE.Vector3()).add(l).multiplyScalar(0.5);
      }
      return palm(person.arms.r.hand, person.arms.r.knuckle, new THREE.Vector3());
    },
  };
}

/**
 * The fielding side for this bowler. `pose(hit, after, ballAt)` places everyone and returns where
 * the ball is when a fielder holds it, or null.
 */
export async function createFielders(scene, bowlerId, bowlType, kit) {
  const field = FIELDS[bowlType];
  let gltf = null;
  try {
    gltf = await new GLTFLoader().loadAsync(`/player-assets/animations/scripted/fielder_${bowlerId}.glb`);
  } catch {
    console.info(`No rigged fielders for ${bowlerId}, using simple figures.`);
  }
  const side = gltf ? riggedFielders(scene, field, gltf) : simpleFielders(scene, field, kit);
  side.field = field;
  side.pose(null, 0);
  return side;
}
