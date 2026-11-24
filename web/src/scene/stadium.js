// Stadium, ground, pitch, stumps and lighting. All procedural: no external assets.
import * as THREE from "three";
import { BOUNDARY } from "../sim/hit.js";

const STAND_INNER = 84;

function canvasTexture(width, height, draw) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  draw(canvas.getContext("2d"), width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function speckle(ctx, w, h, count, colors, size) {
  for (let i = 0; i < count; i++) {
    ctx.fillStyle = colors[Math.floor(Math.random() * colors.length)];
    ctx.fillRect(Math.random() * w, Math.random() * h, size, size);
  }
}

function addGround(scene) {
  const texture = canvasTexture(2048, 2048, (ctx, w, h) => {
    const stripes = 26;
    for (let i = 0; i < stripes; i++) {
      ctx.fillStyle = i % 2 ? "#3f7f35" : "#4a8c3c";
      ctx.fillRect(0, (i * h) / stripes, w, h / stripes + 1);
    }
    speckle(ctx, w, h, 90000, ["rgba(20,60,20,.16)", "rgba(130,175,90,.13)"], 2);
  });
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(STAND_INNER + 2, 96),
    new THREE.MeshStandardMaterial({ map: texture, roughness: 0.95 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const rope = new THREE.Mesh(
    new THREE.TorusGeometry(BOUNDARY, 0.16, 8, 160),
    new THREE.MeshStandardMaterial({ color: 0xf2f2ee, roughness: 0.6 }),
  );
  rope.rotation.x = Math.PI / 2;
  rope.position.y = 0.12;
  scene.add(rope);

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(27.4, 27.6, 96),
    new THREE.MeshBasicMaterial({ color: 0xe8e8e0, transparent: true, opacity: 0.4 }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.012;
  scene.add(ring);
}

function addPitch(scene) {
  const length = 24;
  const width = 3.4;
  const scale = 60;
  const texture = canvasTexture(width * scale, length * scale, (ctx, w, h) => {
    ctx.fillStyle = "#c9b483";
    ctx.fillRect(0, 0, w, h);
    speckle(ctx, w, h, 16000, ["rgba(120,95,55,.2)", "rgba(235,220,180,.2)", "rgba(95,110,60,.12)"], 2);
    for (const end of [-1, 1]) {
      const worn = ctx.createRadialGradient(w / 2, h / 2 + end * 8.2 * scale, 8, w / 2, h / 2 + end * 8.2 * scale, 2.1 * scale);
      worn.addColorStop(0, "rgba(135,105,65,.42)");
      worn.addColorStop(1, "rgba(135,105,65,0)");
      ctx.fillStyle = worn;
      ctx.fillRect(0, 0, w, h);
      const line = (z, x0, x1) => ctx.fillRect(w / 2 + x0 * scale, h / 2 + end * z * scale - 2, (x1 - x0) * scale, 4);
      ctx.fillStyle = "#f7f6ef";
      line(10.06, -1.32, 1.32);
      line(8.84, -1.7, 1.7);
      for (const side of [-1, 1]) {
        ctx.fillRect(w / 2 + side * 1.32 * scale - 2, h / 2 + end * 8.84 * scale - (end > 0 ? 0 : 1.22 * scale), 4, 1.22 * scale + 50);
      }
    }
  });
  const pitch = new THREE.Mesh(
    new THREE.PlaneGeometry(width, length),
    new THREE.MeshStandardMaterial({ map: texture, roughness: 0.9 }),
  );
  pitch.rotation.x = -Math.PI / 2;
  pitch.position.y = 0.01;
  pitch.receiveShadow = true;
  scene.add(pitch);
}

/** Three stumps and two bails. Returns a handle that can knock them over. */
function makeWicket(z) {
  const group = new THREE.Group();
  const wood = new THREE.MeshStandardMaterial({ color: 0xe7c98f, roughness: 0.55 });
  const stumps = [-0.114, 0, 0.114].map((x) => {
    const stump = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.711, 12), wood);
    stump.position.set(x, 0.356, 0);
    stump.castShadow = true;
    group.add(stump);
    return stump;
  });
  const bails = [-0.057, 0.057].map((x) => {
    const bail = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.11, 8), wood);
    bail.rotation.z = Math.PI / 2;
    bail.position.set(x, 0.718, 0);
    group.add(bail);
    return bail;
  });
  group.position.z = z;
  return {
    group,
    reset() {
      stumps.forEach((s, i) => { s.rotation.set(0, 0, 0); s.position.set([-0.114, 0, 0.114][i], 0.356, 0); });
      bails.forEach((b, i) => { b.rotation.set(0, 0, Math.PI / 2); b.position.set([-0.057, 0.057][i], 0.718, 0); });
    },
    knock(f) {
      stumps[1].rotation.x = -0.5 * f;
      stumps[0].rotation.z = 0.2 * f;
      stumps[2].rotation.z = -0.16 * f;
      bails.forEach((b, i) => {
        b.position.set((i ? 0.057 : -0.057) + (i ? 0.3 : -0.3) * f, 0.718 + 0.35 * Math.sin(Math.min(f, 1) * Math.PI) - 0.68 * f * f, -0.45 * f);
        b.rotation.x = 7 * f;
      });
    },
  };
}

function addStands(scene) {
  const profile = [
    [STAND_INNER, 0], [STAND_INNER, 2.2], [STAND_INNER + 16, 13], [STAND_INNER + 16.6, 13],
    [STAND_INNER + 17, 15.5], [STAND_INNER + 31, 27], [STAND_INNER + 33, 33], [STAND_INNER + 36, 33], [STAND_INNER + 36, 0],
  ].map(([r, y]) => new THREE.Vector2(r, y));
  const bowl = new THREE.Mesh(
    new THREE.LatheGeometry(profile, 96),
    new THREE.MeshStandardMaterial({ color: 0x4b5563, roughness: 0.85, side: THREE.DoubleSide }),
  );
  scene.add(bowl);

  const roof = new THREE.Mesh(
    new THREE.RingGeometry(STAND_INNER + 19, STAND_INNER + 38, 96),
    new THREE.MeshStandardMaterial({ color: 0xd8dde3, roughness: 0.5, side: THREE.DoubleSide }),
  );
  roof.rotation.x = Math.PI / 2;
  roof.position.y = 36;
  scene.add(roof);

  const hoardings = canvasTexture(2048, 64, (ctx, w, h) => {
    const colors = ["#16324f", "#b3261e", "#0f766e", "#b45309", "#334155", "#6d28d9"];
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = colors[i];
      ctx.fillRect((i * w) / 6, 0, w / 6 + 1, h);
      ctx.fillStyle = "rgba(255,255,255,.88)";
      ctx.font = "bold 34px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("CROSS-ERA DUEL", ((i + 0.5) * w) / 6, 44);
    }
  });
  hoardings.wrapS = THREE.RepeatWrapping;
  hoardings.repeat.x = -11; // negative: the inside of the cylinder would mirror the text
  const board = new THREE.Mesh(
    new THREE.CylinderGeometry(STAND_INNER - 0.4, STAND_INNER - 0.4, 1.5, 96, 1, true),
    new THREE.MeshBasicMaterial({ map: hoardings, side: THREE.BackSide }),
  );
  board.position.y = 0.75;
  scene.add(board);

  const crowdColors = [0x2563eb, 0xf8fafc, 0xf59e0b, 0xdc2626, 0x1e3a8a, 0x10b981, 0xe2e8f0, 0x7c3aed].map((c) => new THREE.Color(c));
  const count = 30000;
  const crowd = new THREE.InstancedMesh(new THREE.BoxGeometry(0.4, 0.62, 0.36), new THREE.MeshLambertMaterial(), count);
  const matrix = new THREE.Matrix4();
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const upper = Math.random() < 0.46;
    const f = Math.random();
    const radius = upper ? STAND_INNER + 17.6 + f * 12.6 : STAND_INNER + 0.7 + f * 14.6;
    const y = upper ? 16 + f * 10.6 : 2.7 + f * 9.8;
    matrix.makeRotationY(-angle);
    matrix.setPosition(Math.cos(angle) * radius, y + 0.32, Math.sin(angle) * radius);
    crowd.setMatrixAt(i, matrix);
    crowd.setColorAt(i, crowdColors[Math.floor(Math.random() * crowdColors.length)]);
  }
  scene.add(crowd);

  for (const z of [-BOUNDARY - 1.5, BOUNDARY + 1.5]) {
    const screen = new THREE.Mesh(new THREE.BoxGeometry(17, 7, 0.3), new THREE.MeshStandardMaterial({ color: 0xf4f4f0 }));
    screen.position.set(0, 3.5, z);
    scene.add(screen);
  }

  const steel = new THREE.MeshStandardMaterial({ color: 0x9ca3af, metalness: 0.5, roughness: 0.45 });
  const lamp = new THREE.MeshBasicMaterial({ color: 0xfff7d6 });
  for (const angle of [0.75, 2.39, 3.89, 5.53]) {
    const tower = new THREE.Group();
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 1.3, 58, 10), steel);
    mast.position.y = 29;
    tower.add(mast);
    const head = new THREE.Mesh(new THREE.BoxGeometry(13, 6, 0.6), steel);
    head.position.y = 60;
    tower.add(head);
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 7; c++) {
        const bulb = new THREE.Mesh(new THREE.CircleGeometry(0.62, 12), lamp);
        bulb.position.set(-5.4 + c * 1.8, 58.2 + r * 1.8, 0.33);
        tower.add(bulb);
      }
    }
    tower.position.set(Math.cos(angle) * 128, 0, Math.sin(angle) * 128);
    tower.lookAt(0, 8, 0);
    scene.add(tower);
  }
}

function addSky(scene) {
  const texture = canvasTexture(16, 512, (ctx, w, h) => {
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, "#2f6db3");
    sky.addColorStop(0.42, "#8cbce4");
    sky.addColorStop(0.52, "#e7eef2");
    sky.addColorStop(1, "#c4d2d8");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);
  });
  scene.add(new THREE.Mesh(new THREE.SphereGeometry(420, 32, 16), new THREE.MeshBasicMaterial({ map: texture, side: THREE.BackSide, fog: false })));
}

function addLights(scene) {
  scene.add(new THREE.HemisphereLight(0xdcecff, 0x4e6a3a, 1.25));
  const sun = new THREE.DirectionalLight(0xfff1dc, 2.7);
  sun.position.set(-26, 46, 18);
  sun.target.position.set(0, 0, -2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -18, right: 18, top: 20, bottom: -20, near: 5, far: 110 });
  sun.shadow.bias = -0.0004;
  scene.add(sun, sun.target);
}

export function buildStadium(scene) {
  scene.fog = new THREE.Fog(0xcbdde8, 190, 430);
  addSky(scene);
  addLights(scene);
  addGround(scene);
  addPitch(scene);
  addStands(scene);
  const striker = makeWicket(-10.06);
  const bowlerEnd = makeWicket(10.06);
  scene.add(striker.group, bowlerEnd.group);
  return { striker, bowlerEnd };
}
