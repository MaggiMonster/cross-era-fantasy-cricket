// Placeholder capsule players. Turns 5 and 6 replace these with rigged glTF characters
// that keep the same small API: root, setRunUp(f), setSwing(shot, f), reset().
import * as THREE from "three";

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

export function createBatter(id) {
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
    setSwing(shot, f) {
      const [from, to] = SWINGS[shot] ?? SWINGS.defend;
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
