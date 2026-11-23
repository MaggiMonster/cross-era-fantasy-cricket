// The 3D duel. The networks (model/duel.js) decide every ball before it is animated.
// URL options: ?matchup=kohli-warne&seed=1&auto=1&overs=3&lives=3
// &frames=N advances N fixed 1/60 s steps and then holds, for automated checks and screenshots.
// &motion=scripted picks the animation source. &pose=drive:0.4 holds a close-up of one shot.
// &closeup=1 starts in the close view. The C key switches views at any time.
import * as THREE from "three";
import { Duel, Networks, mulberry32 } from "./model/duel.js";
import { LENGTHS, LINES, SHOTS, bowlingKey, shotForKey } from "./controls.js";
import { showMenu } from "./menu.js";
import { clipFor } from "./shots.js";
import { createBatter, createBowler, KIT, SWING } from "./scene/players.js";
import { buildStadium } from "./scene/stadium.js";
import { deliveryPath, placeholderHit, sampleAt, BALL_RADIUS, BOWLERS, RELEASE_Z } from "./sim/ball.js";

// Each view has a wide framing before the ball and a tight one by the time it is bowled.
const shotView = (px, py, pz, tx, ty, tz, fov) => ({ position: new THREE.Vector3(px, py, pz), target: new THREE.Vector3(tx, ty, tz), fov });
const CLOSE = shotView(-6.2, 1.45, -7.4, 0.05, 0.55, -8.75, 34);
const VIEWS = {
  normal: { wide: shotView(1.2, 4.8, 33, 0, -0.55, -1.5, 19), tight: shotView(1.4, 3.4, 22, 0, 0.35, -5, 15) },
  close: { wide: CLOSE, tight: CLOSE },
};
const LABEL = { outside_off: "outside off", stumps: "on the stumps", leg: "down leg", run_out: "run out" };

const params = new URLSearchParams(location.search);
const [batterId, bowlerId] = (params.get("matchup") ?? "tendulkar-bumrah").split("-");
const requestedMode = params.get("mode") ?? (params.get("auto") === "1" ? "auto" : "bat");
const mode = ["bat", "bowl", "auto"].includes(requestedMode) ? requestedMode : "bat";
const auto = mode === "auto";
const HINTS = {
  bat: "Arrows: ↑ drive, ↓ defend, ← cut, → work. With Shift: loft, sweep, leave, pull. Keys 1-8 also work. Space lets the batting network choose. C switches view. Data: Cricsheet, CC BY 4.0.",
  bowl: "Keys 1-5 pick the length. ← off, ↓ stumps, → leg pick the line. Enter or Space bowls. The batting network replies. C switches view. Data: Cricsheet, CC BY 4.0.",
  auto: "Auto mode: the networks play both sides. C switches view. Data: Cricsheet, CC BY 4.0.",
};
const seedParam = params.get("seed");
const positive = (name, fallback) => {
  const value = Number.parseInt(params.get(name) ?? "", 10);
  return value >= 1 ? value : fallback;
};

const $ = (id) => document.getElementById(id);
const ballStart = (id) => ({ x: BOWLERS[id].releaseX, y: BOWLERS[id].releaseHeight, z: RELEASE_Z });

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
  let view = params.has("closeup") ? "close" : "normal";
  let push = 0;
  const camera = new THREE.PerspectiveCamera(VIEWS[view].wide.fov, innerWidth / innerHeight, 0.1, 900);
  const look = new THREE.Vector3();
  function applyView() {
    const { wide, tight } = VIEWS[view];
    camera.position.lerpVectors(wide.position, tight.position, push);
    look.lerpVectors(wide.target, tight.target, push);
    camera.fov = wide.fov + (tight.fov - wide.fov) * push;
    camera.updateProjectionMatrix();
    camera.lookAt(look);
  }
  applyView();

  const { striker } = buildStadium(scene);
  const batter = await createBatter(batterId, params.get("motion") ?? "scripted");
  const bowler = await createBowler(bowlerId, params.get("motion") ?? "scripted");
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
    push = 0;
    applyView();
    if (mode === "bowl") {
      showPlan();
    } else {
      const d = duel.nextDelivery();
      $("delivery").textContent = `Next ball: ${d.bowl_type}, ${d.length}, ${LABEL[d.line]}`;
    }
    $("result").textContent = "";
    $("shots").classList.remove("locked");
    $("bowling").classList.remove("locked");
    scoreboard();
    phase = "await";
    clock = 0;
  }

  // The human bowler's plan carries over from ball to ball until it is changed.
  const plan = { length: "good", line: "stumps" };
  function showPlan() {
    $("delivery").textContent = `Your ball: ${plan.length}, ${LABEL[plan.line]}`;
    for (const button of $("bowl-lengths").children) button.classList.toggle("active", button.dataset.length === plan.length);
    for (const button of $("bowl-lines").children) {
      if (button.dataset.line) button.classList.toggle("active", button.dataset.line === plan.line);
    }
  }
  function setPlan(change) {
    if (phase !== "await") return;
    Object.assign(plan, change);
    showPlan();
  }
  function bowlPlan() {
    if (phase !== "await") return;
    duel.chooseDelivery(plan.length, plan.line);
    playBall(null);
  }

  function playBall(shot) {
    if (phase !== "await") return;
    const delivery = duel.nextDelivery();
    const result = duel.play(shot);
    const jitter = { speed: (visual() - 0.5) * 1.6, length: (visual() - 0.5) * 0.4, line: (visual() - 0.5) * 0.08 };
    const path = deliveryPath(bowlerId, delivery, jitter);
    // When the bat connects, the swing is steered to the ball and timed to meet it there.
    const connects = result.shot !== "leave" && !["bowled", "lbw", "stumped"].includes(result.outcome);
    const clip = clipFor(result.shot, delivery.length);
    if (!connects) batter.clearAim();
    const contact = (connects && batter.planContact(clip, path.points)) || path.crease;
    ballView = { result, clip, path, contact, hit: null, hitAt: 0 };
    $("shots").classList.add("locked");
    $("bowling").classList.add("locked");
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
    batter.update(dt);
    bowler.update(dt);
    if (phase === "await" && auto && clock > 0.35) playBall(null);
    if (phase === "runup") {
      const f = Math.min(clock / bowler.runUpSeconds, 1);
      bowler.setRunUp(f);
      const inHand = bowler.ballPoint();
      if (inHand) { ball.visible = true; ball.position.copy(inHand); }
      push = f * f * (3 - 2 * f);
      if (f >= 1) { phase = "flight"; clock = 0; ball.visible = true; }
    }
    if (phase === "flight") {
      const { path, result, clip, contact } = ballView;
      bowler.followThrough(Math.min(clock / 0.8, 1));
      placeBall(sampleAt(path.points, clock));
      const swingStart = contact.t - SWING.lead;
      if (clock > swingStart) batter.setSwing(clip, Math.min((clock - swingStart) / SWING.time, 1));
      if (clock >= contact.t) {
        ballView.hit = placeholderHit(contact, result.shot, result.outcome);
        showResult();
        phase = ballView.hit ? "hit" : "past";
        clock = 0;
      }
    } else if (phase === "past") {
      const { path, result, clip, contact } = ballView;
      const t = contact.t + clock;
      placeBall(sampleAt(path.points, t));
      batter.setSwing(clip, Math.min((clock + SWING.lead) / SWING.time, 1));
      if (result.outcome === "stumped" || result.outcome === "bowled") striker.knock(Math.min(clock / 0.3, 1));
      if (clock > 1.25) finishBall();
    } else if (phase === "hit") {
      const { hit, result, clip } = ballView;
      batter.setSwing(clip, Math.min((clock + SWING.lead) / SWING.time, 1));
      placeBall(sampleAt(hit, clock));
      const end = hit[hit.length - 1].t;
      if (result.outcome === "bowled" || result.outcome === "run_out") striker.knock(Math.min(Math.max(clock - (result.outcome === "bowled" ? end : 0.5), 0) / 0.32, 1));
      if (hit.length > 2 && view === "normal") {
        look.lerp(ball.position, 1 - Math.exp(-dt * 3.2));
        camera.fov += (34 - camera.fov) * (1 - Math.exp(-dt * 2));
        camera.updateProjectionMatrix();
      }
      if (clock > end + 0.95) finishBall();
    }
    const following = phase === "hit" && view === "normal" && ballView.hit.length > 2;
    if (following) camera.lookAt(look);
    else applyView();
  }

  function switchView() {
    view = view === "normal" ? "close" : "normal";
    $("view").textContent = view === "normal" ? "Close view (C)" : "Normal view (C)";
    applyView();
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
  LENGTHS.forEach((length, i) => {
    const button = document.createElement("button");
    button.dataset.length = length;
    button.innerHTML = `<kbd>${i + 1}</kbd>${length}`;
    button.addEventListener("click", (event) => { setPlan({ length }); event.currentTarget.blur(); });
    $("bowl-lengths").appendChild(button);
  });
  LINES.forEach((line, i) => {
    const button = document.createElement("button");
    button.dataset.line = line;
    button.innerHTML = `<kbd>${["←", "↓", "→"][i]}</kbd>${LABEL[line]}`;
    button.addEventListener("click", (event) => { setPlan({ line }); event.currentTarget.blur(); });
    $("bowl-lines").appendChild(button);
  });
  const bowlButton = document.createElement("button");
  bowlButton.innerHTML = "<kbd>Enter</kbd>Bowl";
  bowlButton.addEventListener("click", (event) => { bowlPlan(); event.currentTarget.blur(); });
  $("bowl-lines").appendChild(bowlButton);
  $("shots").hidden = mode !== "bat";
  $("bowling").hidden = mode !== "bowl";
  $("hint").textContent = HINTS[mode];

  addEventListener("keydown", (event) => {
    if (mode === "bowl") {
      const action = bowlingKey(event.key);
      if (action) {
        event.preventDefault();
        if (action.bowl) bowlPlan();
        else setPlan(action);
      }
    } else if (mode === "bat") {
      const chosen = shotForKey(event.key, event.shiftKey);
      if (chosen) {
        event.preventDefault();
        playBall(chosen);
      }
      if (event.code === "Space") { event.preventDefault(); playBall(null); }
    }
    if (event.key.toLowerCase() === "c" && !event.metaKey && !event.ctrlKey) switchView();
    if (event.key.toLowerCase() === "r" && phase === "over") newDuel();
  });
  $("again").addEventListener("click", newDuel);
  $("view").addEventListener("click", (event) => { switchView(); event.currentTarget.blur(); });
  $("view").textContent = view === "normal" ? "Close view (C)" : "Normal view (C)";
  for (const link of document.querySelectorAll("[data-matchup]")) {
    link.classList.toggle("active", link.dataset.matchup === `${batterId}-${bowlerId}`);
  }

  newDuel();
  window.__duel = { get duel() { return duel; }, get phase() { return phase; } };

  const fixedFrames = params.has("frames") ? Number(params.get("frames")) : null;
  for (let i = 0; fixedFrames !== null && i < fixedFrames && phase !== "over"; i++) update(1 / 60);

  // Close-up for reviewing the bowling action: &bowlpose=0.9 holds that fraction of the run-up,
  // and values from 1 to 2 hold the follow-through.
  if (params.has("bowlpose")) {
    const f = Number(params.get("bowlpose"));
    if (f <= 1) bowler.setRunUp(f);
    else bowler.followThrough(f - 1);
    const at = bowler.ballPoint() ?? bowler.root.position;
    ball.visible = true;
    ball.position.copy(at);
    bowler.root.updateMatrixWorld(true);
    const body = new THREE.Box3().setFromObject(bowler.root).getCenter(new THREE.Vector3());
    camera.fov = 30;
    camera.position.set(body.x - 6.5, 1.5, body.z - 1.5);
    camera.lookAt(body.x, 1.05, body.z);
    camera.updateProjectionMatrix();
    document.querySelectorAll("#board,#matchups,#bottom").forEach((el) => { el.hidden = true; el.style.display = "none"; });
    const start = ballStart(bowlerId);
    document.title = `hand ${at.x.toFixed(3)} ${at.y.toFixed(3)} ${at.z.toFixed(3)} physics ${start.x} ${start.y} ${start.z}`;
    renderer.setAnimationLoop(() => renderer.render(scene, camera));
    window.__ready = true;
    return;
  }

  // Close-up for reviewing one shot, seen from the off side.
  const held = params.get("pose")?.split(":");
  if (held) {
    batter.setSwing(held[0], Number(held[1] ?? SWING.lead));
    camera.fov = 30;
    camera.position.set(-5.2, 1.25, -8.2);
    camera.lookAt(0.2, 0.92, -8.85);
    camera.updateProjectionMatrix();
    document.querySelectorAll("#board,#matchups,#bottom").forEach((el) => { el.hidden = true; el.style.display = "none"; });
    renderer.setAnimationLoop(() => renderer.render(scene, camera));
    window.__ready = true;
    return;
  }
  window.__ready = true;

  const timer = new THREE.Timer();
  renderer.setAnimationLoop((time) => {
    timer.update(time);
    if (fixedFrames === null) update(Math.min(timer.getDelta(), 0.05));
    renderer.render(scene, camera);
  });
}

// With no options in the URL the game opens on the menu.
if (location.search === "") {
  showMenu();
} else {
  start().catch((error) => {
    $("error").textContent = `Could not start the game: ${error.message}`;
    $("error").hidden = false;
    throw error;
  });
}
