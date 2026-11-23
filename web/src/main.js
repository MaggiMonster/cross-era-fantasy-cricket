// The 3D duel. The networks (model/duel.js) decide every ball before it is animated.
// URL options: ?matchup=kohli-warne&seed=1&auto=1&overs=3&lives=3
// &frames=N advances N fixed 1/60 s steps and then holds, for automated checks and screenshots.
import * as THREE from "three";
import { Duel, Networks, mulberry32 } from "./model/duel.js";
import { createBatter, createBowler, KIT } from "./scene/players.js";
import { buildStadium } from "./scene/stadium.js";
import { deliveryPath, placeholderHit, sampleAt, BALL_RADIUS } from "./sim/ball.js";

const SHOTS = ["leave", "defend", "work", "drive", "cut", "pull", "sweep", "loft"];
const RUN_UP_SECONDS = { bumrah: 1.7, warne: 1.05 };
const BROADCAST = { position: new THREE.Vector3(0.7, 8.6, 44), target: new THREE.Vector3(0, -0.9, 2.5), fov: 21 };
const LABEL = { outside_off: "outside off", stumps: "on the stumps", leg: "down leg", run_out: "run out" };

const params = new URLSearchParams(location.search);
const [batterId, bowlerId] = (params.get("matchup") ?? "tendulkar-bumrah").split("-");
const auto = params.get("auto") === "1";
const seedParam = params.get("seed");
const positive = (name, fallback) => {
  const value = Number.parseInt(params.get(name) ?? "", 10);
  return value >= 1 ? value : fallback;
};

const $ = (id) => document.getElementById(id);

function setupRenderer() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: params.has("capture") });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  $("stage").appendChild(renderer.domElement);
  return renderer;
}

async function start() {
  const response = await fetch(`${import.meta.env.BASE_URL}data/networks.json`);
  if (!response.ok) throw new Error(`could not load networks (${response.status})`);
  const networks = new Networks(await response.json());

  const renderer = setupRenderer();
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(BROADCAST.fov, innerWidth / innerHeight, 0.1, 900);
  camera.position.copy(BROADCAST.position);
  const look = BROADCAST.target.clone();
  camera.lookAt(look);

  const { striker } = buildStadium(scene);
  const batter = createBatter(batterId);
  const bowler = createBowler(bowlerId);
  scene.add(batter.root, bowler.root);
  const ball = new THREE.Mesh(
    new THREE.SphereGeometry(BALL_RADIUS * 1.5, 18, 12),
    new THREE.MeshStandardMaterial({ color: 0xb91c1c, roughness: 0.35 }),
  );
  ball.castShadow = true;
  ball.visible = false;
  scene.add(ball);

  // Visual variation has its own generator, so it can never change the model's draws.
  const visual = mulberry32(((Number(seedParam) || 7) * 31 + 11) >>> 0);
  let duel;
  let phase;
  let clock = 0;
  let ballView = null;

  function newDuel() {
    const seed = seedParam === null ? (Math.random() * 2 ** 32) >>> 0 : Number(seedParam);
    duel = new Duel(networks, batterId, bowlerId, {
      overs: positive("overs", 3),
      lives: positive("lives", 3),
      random: mulberry32(seed),
    });
    $("banner").hidden = true;
    awaitShot();
  }

  function scoreboard() {
    const balls = duel.ballsBowled;
    $("names").textContent = `${KIT[batterId].name} v ${KIT[bowlerId].name}`;
    $("score").textContent = `${duel.runs}/${duel.livesLost}`;
    $("target").textContent = `Target ${duel.target}`;
    $("overs").textContent = `${Math.floor(balls / 6)}.${balls % 6} / ${duel.overs} ov`;
    $("lives").textContent = "●".repeat(duel.livesLeft) + "○".repeat(duel.livesLost);
    $("need").textContent = duel.isOver ? "" : `Need ${duel.runsNeeded} from ${duel.ballsLeft}`;
  }

  function awaitShot() {
    batter.reset();
    bowler.reset();
    striker.reset();
    ball.visible = false;
    ballView = null;
    camera.position.copy(BROADCAST.position);
    look.copy(BROADCAST.target);
    const d = duel.nextDelivery();
    $("delivery").textContent = `Next ball: ${d.bowl_type}, ${d.length}, ${LABEL[d.line]}`;
    $("result").textContent = "";
    $("shots").classList.remove("locked");
    scoreboard();
    phase = "await";
    clock = 0;
  }

  function playBall(shot) {
    if (phase !== "await") return;
    const delivery = duel.nextDelivery();
    const result = duel.play(shot);
    const jitter = { speed: (visual() - 0.5) * 1.6, length: (visual() - 0.5) * 0.4, line: (visual() - 0.5) * 0.08 };
    ballView = { result, path: deliveryPath(bowlerId, delivery, jitter), hit: null, hitAt: 0 };
    $("shots").classList.add("locked");
    phase = "runup";
    clock = 0;
  }

  function showResult() {
    const { outcome, shot, isWicket } = ballView.result;
    const text = isWicket ? `OUT! ${LABEL[outcome] ?? outcome}` : outcome === "dot" ? "Dot ball" : outcome === "1" ? "1 run" : `${outcome} runs`;
    $("result").textContent = `${shot}: ${text}`;
    $("result").className = isWicket ? "wicket" : outcome === "4" || outcome === "6" ? "boundary" : "";
    scoreboard();
  }

  function finishBall() {
    if (duel.isOver) {
      phase = "over";
      $("banner-title").textContent = duel.batterWon ? `${KIT[batterId].name} WINS` : `${KIT[bowlerId].name} WINS`;
      $("banner-detail").textContent = `${duel.runs}/${duel.livesLost} chasing ${duel.target}, ${duel.ballsBowled} balls`;
      $("banner").hidden = false;
    } else {
      awaitShot();
    }
  }

  function placeBall(p) {
    ball.position.set(p.x, p.y, p.z);
  }

  function update(dt) {
    clock += dt;
    if (phase === "await" && auto && clock > 0.35) playBall(null);
    if (phase === "runup") {
      const f = Math.min(clock / RUN_UP_SECONDS[bowlerId], 1);
      bowler.setRunUp(f);
      if (f >= 1) { phase = "flight"; clock = 0; ball.visible = true; }
    }
    if (phase === "flight") {
      const { path, result } = ballView;
      bowler.followThrough(Math.min(clock / 0.8, 1));
      placeBall(sampleAt(path.points, clock));
      const swingStart = path.crease.t - 0.26;
      if (clock > swingStart) batter.setSwing(result.shot, Math.min((clock - swingStart) / 0.42, 1));
      if (clock >= path.crease.t) {
        ballView.hit = placeholderHit(path.crease, result.shot, result.outcome);
        showResult();
        phase = ballView.hit ? "hit" : "past";
        clock = 0;
      }
    } else if (phase === "past") {
      const { path, result } = ballView;
      const t = path.crease.t + clock;
      placeBall(sampleAt(path.points, t));
      batter.setSwing(result.shot, Math.min((t - path.crease.t + 0.26) / 0.42, 1));
      if (result.outcome === "stumped") striker.knock(Math.min(clock / 0.3, 1));
      if (clock > 1.25) finishBall();
    } else if (phase === "hit") {
      const { hit, result } = ballView;
      batter.setSwing(result.shot, Math.min((clock + 0.26) / 0.42, 1));
      placeBall(sampleAt(hit, clock));
      const end = hit[hit.length - 1].t;
      if (result.outcome === "bowled" || result.outcome === "run_out") striker.knock(Math.min(Math.max(clock - (result.outcome === "bowled" ? end : 0.5), 0) / 0.32, 1));
      if (hit.length > 2) {
        look.lerp(ball.position, 1 - Math.exp(-dt * 3.2));
        camera.fov += (34 - camera.fov) * (1 - Math.exp(-dt * 2));
        camera.updateProjectionMatrix();
      }
      if (clock > end + 0.95) {
        camera.fov = BROADCAST.fov;
        camera.updateProjectionMatrix();
        finishBall();
      }
    }
    camera.lookAt(look);
  }

  addEventListener("resize", () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });

  const buttons = $("shots");
  SHOTS.forEach((shot, i) => {
    const button = document.createElement("button");
    button.innerHTML = `<kbd>${i + 1}</kbd>${shot}`;
    button.addEventListener("click", () => playBall(shot));
    buttons.appendChild(button);
  });
  addEventListener("keydown", (event) => {
    const n = Number(event.key);
    if (n >= 1 && n <= 8) playBall(SHOTS[n - 1]);
    if (event.code === "Space") { event.preventDefault(); playBall(null); }
    if (event.key.toLowerCase() === "r" && phase === "over") newDuel();
  });
  $("again").addEventListener("click", newDuel);
  for (const link of document.querySelectorAll("[data-matchup]")) {
    link.classList.toggle("active", link.dataset.matchup === `${batterId}-${bowlerId}`);
  }

  newDuel();
  window.__duel = { get duel() { return duel; }, get phase() { return phase; } };

  const fixedFrames = params.has("frames") ? Number(params.get("frames")) : null;
  for (let i = 0; fixedFrames !== null && i < fixedFrames && phase !== "over"; i++) update(1 / 60);

  const timer = new THREE.Timer();
  renderer.setAnimationLoop((time) => {
    timer.update(time);
    if (fixedFrames === null) update(Math.min(timer.getDelta(), 0.05));
    renderer.render(scene, camera);
  });
}

start().catch((error) => {
  $("error").textContent = `Could not start the game: ${error.message}`;
  $("error").hidden = false;
  throw error;
});
