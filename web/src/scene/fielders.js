// The fielding side: simple jointed figures in the bowler's kit. Their positions come from
// fielderStates in sim/hit.js, so a live ball and its replay always look the same.
import * as THREE from "three";
import { FIELDS, fielderStates } from "../sim/hit.js";

const STRIDE_RATE = 11; // Radians of leg swing per second while running.

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

export function createFielders(scene, bowlType, kit) {
  const field = FIELDS[bowlType];
  const shirt = new THREE.MeshStandardMaterial({ color: kit.shirt, roughness: 0.6 });
  const trousers = new THREE.MeshStandardMaterial({ color: 0x172554, roughness: 0.7 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xc99a76, roughness: 0.6 });
  const figures = field.map((_, i) => figure(shirt, trousers, skin, i === 0));
  for (const f of figures) scene.add(f.root);

  /** Pose everyone `after` seconds past contact. A null hit leaves them in position. */
  function pose(hit, after, ballAt) {
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
  }
  pose(null, 0);
  return { pose, field };
}
