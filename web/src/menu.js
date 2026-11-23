// The start menu: character select, mode, overs and lives. Starting a game opens the URL
// the game already understands. Portraits are rendered from each player's 3D head, so they
// update by themselves when the FaceBuilder heads replace the placeholders.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { KIT } from "./scene/players.js";

const PLAYERS = [
  { id: "tendulkar", name: "Sachin Tendulkar", role: "Batter · old era", matchup: "tendulkar-bumrah" },
  { id: "kohli", name: "Virat Kohli", role: "Batter · new era", matchup: "kohli-warne" },
  { id: "bumrah", name: "Jasprit Bumrah", role: "Pace · new era", matchup: "tendulkar-bumrah" },
  { id: "warne", name: "Shane Warne", role: "Leg-spin · old era", matchup: "kohli-warne" },
];
const MODES = [
  { id: "bat", label: "You bat" },
  { id: "bowl", label: "You bowl" },
  { id: "auto", label: "Auto" },
];
const DUEL_NAME = { "tendulkar-bumrah": "Sachin v Bumrah", "kohli-warne": "Kohli v Warne" };

/** Render one head to an image, or return null if the character is not available. */
async function portrait(id, renderer) {
  let gltf;
  try {
    gltf = await new GLTFLoader().loadAsync(`/player-assets/characters/${id}.glb`);
  } catch {
    return null;
  }
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1e3a5f);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 2.4);
  sun.position.set(-1, 2, 3);
  scene.add(sun, gltf.scene);
  gltf.scene.updateMatrixWorld(true);
  const head = gltf.scene.getObjectByName("head");
  if (!head) return null;
  const at = head.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.09, 0));
  const camera = new THREE.PerspectiveCamera(24, 1, 0.05, 10);
  camera.position.set(at.x - 0.28, at.y + 0.04, at.z + 1.05); // The models face +Z.
  camera.lookAt(at);
  renderer.render(scene, camera);
  return renderer.domElement.toDataURL("image/png");
}

export function showMenu() {
  const menu = document.getElementById("menu");
  const choice = { matchup: "tendulkar-bumrah", mode: "bat" };
  menu.hidden = false;

  const cards = document.getElementById("menu-players");
  const portraits = new Map();
  for (const player of PLAYERS) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "card";
    card.dataset.matchup = player.matchup;
    card.setAttribute("aria-label", `${player.name}, ${DUEL_NAME[player.matchup]}`);
    const color = `#${KIT[player.id].shirt.toString(16).padStart(6, "0")}`;
    card.innerHTML = `<span class="face" style="background-color:${color}">${KIT[player.id].number}</span><strong>${player.name}</strong><small>${player.role}</small>`;
    card.addEventListener("click", () => { choice.matchup = player.matchup; refresh(); });
    cards.appendChild(card);
    portraits.set(player.id, card.querySelector(".face"));
  }

  const modes = document.getElementById("menu-modes");
  for (const mode of MODES) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.mode = mode.id;
    button.textContent = mode.label;
    button.addEventListener("click", () => { choice.mode = mode.id; refresh(); });
    modes.appendChild(button);
  }

  function refresh() {
    for (const card of cards.children) {
      const on = card.dataset.matchup === choice.matchup;
      card.classList.toggle("active", on);
      card.setAttribute("aria-pressed", String(on));
    }
    for (const button of modes.children) {
      const on = button.dataset.mode === choice.mode;
      button.classList.toggle("active", on);
      button.setAttribute("aria-pressed", String(on));
    }
    document.getElementById("menu-duel").textContent = DUEL_NAME[choice.matchup];
  }
  refresh();

  document.getElementById("menu-start").addEventListener("click", () => {
    const query = new URLSearchParams({
      matchup: choice.matchup,
      mode: choice.mode,
      overs: document.getElementById("menu-overs").value,
      lives: document.getElementById("menu-lives").value,
    });
    location.search = query.toString();
  });

  // Portraits load after the menu is usable. A missing character keeps its kit number.
  (async () => {
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(192, 192);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    for (const player of PLAYERS) {
      const image = await portrait(player.id, renderer);
      if (!image) continue;
      const face = portraits.get(player.id);
      face.textContent = "";
      face.style.backgroundImage = `url(${image})`;
    }
    renderer.dispose();
    window.__menuReady = true;
  })().catch((error) => console.warn("Portraits unavailable", error));
}
