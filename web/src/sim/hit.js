// Where the ball goes after the bat, from the shot and the outcome the networks already chose.
// No Three.js here, so Node can test it. Same axes as ball.js: +x leg side, +z towards the bowler.
// Presentation only: `random` must be the visual generator, never the model's.
import { BALL_RADIUS, PITCH_HALF, sampleAt } from "./ball.js";

export const BOUNDARY = 72;
const GRAVITY = 9.81;
export const FIELDER_SPEED = 7; // Metres per second, a prior for a sprinting fielder.
export const REACT = 0.25; // Seconds before a fielder starts to move.
const THROW_SPEED = 30;
// Timings of the fielder clips in pipeline/build_fielder.py, in seconds from each clip's start.
export const FIELD_CLIP = { catchReach: 10 / 30, pickup: 6 / 30, release: 19 / 30 };
const THROW_WINDUP = FIELD_CLIP.release - FIELD_CLIP.pickup;
const CATCH_HEIGHT = 1.3; // Chest height, with the hands out in front.
const HANDS_AHEAD = 0.45; // Metres from a fielder's body to the ball in his hands.
const PICKUP_REACH = 0.55; // A fielder stops this far short of a ball he picks up.
const RELEASE_HEIGHT = 1.8;
const SIX_PAST_ROPE = 7.5; // Metres beyond the rope that a six lands, short of the stands.
const STUMPS = { x: 0, y: 0.6, z: -PITCH_HALF };

// Nine fielders plus the bowler and keeper. Index 0 is always the keeper and 1 the slip.
export const FIELDS = {
  pace: [
    { name: "keeper", x: -0.2, z: -13.5 }, { name: "slip", x: -1.6, z: -14.5 },
    { name: "point", x: -26, z: -9 }, { name: "cover", x: -23, z: 6 },
    { name: "mid-off", x: -10, z: 24 }, { name: "mid-on", x: 10, z: 24 },
    { name: "midwicket", x: 24, z: 4 }, { name: "square leg", x: 26, z: -11 },
    { name: "deep third", x: -40, z: -56 }, { name: "fine leg", x: 38, z: -58 },
  ],
  spin: [
    { name: "keeper", x: -0.1, z: -11.2 }, { name: "slip", x: -1.2, z: -12.2 },
    { name: "point", x: -22, z: -10 }, { name: "cover", x: -22, z: 5 },
    { name: "mid-off", x: -12, z: 26 }, { name: "mid-on", x: 12, z: 26 },
    { name: "midwicket", x: 24, z: 2 }, { name: "square leg", x: 24, z: -12 },
    { name: "deep cover", x: -52, z: 36 }, { name: "long-on", x: 30, z: 60 },
  ],
};

// Centre and half-width of each shot's arc (radians, 0 straight back past the bowler, + leg side).
export const SECTORS = {
  defend: [0.1, 0.5], work: [1.2, 0.5], drive: [-0.35, 0.45], cut: [-1.75, 0.4],
  pull: [1.85, 0.45], sweep: [2.2, 0.4], loft: [0.1, 0.6], leave: [0, 0],
};
const LINE_SHIFT = { outside_off: -0.18, stumps: 0, leg: 0.18 };
// Distance band (m) and ball speed off the bat and at the end (m/s) for each ground outcome.
const GROUND = {
  dot: { band: [6, 14], v0: 14, v1: 0 },
  1: { band: [16, 30], v0: 20, v1: 0 },
  2: { band: [34, 48], v0: 25, v1: 0 },
  3: { band: [50, 60], v0: 29, v1: 0 },
  run_out: { band: [12, 24], v0: 20, v1: 0 },
};
const EDGED = new Set(["defend", "drive", "cut", "work"]);

const between = (random, [low, high]) => low + (high - low) * random();
const clamp01 = (x) => Math.min(Math.max(x, 0), 1);
const direction = (angle) => ({ x: Math.sin(angle), z: Math.cos(angle) });

/** Metres from `p` to the boundary rope along direction `d`. */
export function ropeDistance(p, d) {
  const b = p.x * d.x + p.z * d.z;
  return -b + Math.sqrt(Math.max(b * b - (p.x * p.x + p.z * p.z) + BOUNDARY * BOUNDARY, 0));
}

function groundPath(from, d, distance, v0, v1) {
  const duration = (2 * distance) / (v0 + v1);
  const decel = (v0 - v1) / duration;
  const points = [];
  for (let i = 0; i <= 60; i++) {
    const t = (i / 60) * duration;
    const s = v0 * t - 0.5 * decel * t * t;
    const hop = Math.max(from.y - BALL_RADIUS, 0) * Math.exp(-6 * t) * Math.abs(Math.cos(7 * t));
    points.push({ t, x: from.x + d.x * s, y: BALL_RADIUS + hop, z: from.z + d.z * s });
  }
  return points;
}

/** A parabola between two points that takes `duration` seconds, starting at time `t0`. */
function airPath(from, to, duration, t0 = 0) {
  const rise = (GRAVITY * duration * duration) / 8;
  const points = [];
  for (let i = 0; i <= 60; i++) {
    const f = i / 60;
    points.push({
      t: t0 + f * duration,
      x: from.x + (to.x - from.x) * f,
      y: Math.max(BALL_RADIUS, from.y + (to.y - from.y) * f + 4 * rise * f * (1 - f)),
      z: from.z + (to.z - from.z) * f,
    });
  }
  return points;
}

/** Smallest gap between the ball and what any fielder can cover. Positive means nobody gets there. */
function clearance(points, field, until = 1) {
  let least = Infinity;
  const last = Math.floor((points.length - 1) * until);
  for (let i = 0; i <= last; i += 3) {
    const p = points[i];
    for (const f of field) {
      const reach = FIELDER_SPEED * Math.max(p.t - REACT, 0) + 1;
      least = Math.min(least, Math.hypot(p.x - f.x, p.z - f.z) - reach);
    }
  }
  return least;
}

/** Try angles across the shot's arc and take one of the best gaps, widening if none is clear. */
function chooseGap(from, shot, line, field, random, build, until) {
  const [centre, half] = SECTORS[shot];
  const middle = centre + (LINE_SHIFT[line] ?? 0);
  let best = [];
  for (const widen of [1, 1.6, 2.4]) {
    best = [];
    for (let i = 0; i < 15; i++) {
      const angle = middle + half * widen * (i / 7 - 1);
      const points = build(direction(angle));
      best.push({ angle, points, gap: clearance(points, field, until) });
    }
    best.sort((a, b) => b.gap - a.gap);
    if (best[0].gap > 0) break;
  }
  const clear = best.filter((c) => c.gap > 0).slice(0, 3);
  const pool = clear.length ? clear : best.slice(0, 1);
  return pool[Math.floor(random() * pool.length)];
}

function nearestFielder(field, target) {
  let index = 0;
  let least = Infinity;
  field.forEach((f, i) => {
    const distance = Math.hypot(f.x - target.x, f.z - target.z);
    if (distance < least) { least = distance; index = i; }
  });
  return { index, distance: least };
}

function plan(kind, points, extra = {}) {
  return { kind, points, end: points[points.length - 1].t, fielder: null, action: null, target: null, arriveT: 0, throwAt: null, stumpsAt: null, ...extra };
}

function planCatch(from, shot, line, field, random) {
  let index;
  if (EDGED.has(shot)) {
    index = random() < 0.5 ? 0 : 1;
  } else {
    const aim = SECTORS[shot][0] + (LINE_SHIFT[line] ?? 0);
    let least = Infinity;
    field.forEach((f, i) => {
      if (Math.hypot(f.x - from.x, f.z - from.z) < 15) return;
      const off = Math.abs(Math.atan2(Math.sin(Math.atan2(f.x - from.x, f.z - from.z) - aim), Math.cos(Math.atan2(f.x - from.x, f.z - from.z) - aim)));
      if (off < least) { least = off; index = i; }
    });
  }
  const f = field[index];
  const span = Math.hypot(f.x - from.x, f.z - from.z);
  const close = span < 10;
  const step = close ? 0 : 1 + 2 * random();
  // The fielder moves `step` towards the batter, and the ball meets his hands just in front of him.
  const towards = { x: (from.x - f.x) / span, z: (from.z - f.z) / span };
  const target = { x: f.x + towards.x * step, z: f.z + towards.z * step };
  const hands = { x: target.x + towards.x * HANDS_AHEAD, y: CATCH_HEIGHT, z: target.z + towards.z * HANDS_AHEAD };
  const duration = close ? 0.45 : Math.min(Math.max(span / 17, 1.8), 3.6);
  const points = airPath(from, hands, duration);
  return plan("caught", points, { fielder: index, action: "catch", target, hands, arriveT: REACT + step / FIELDER_SPEED });
}

function planSix(from, shot, line, field, random) {
  const build = (d) => {
    const carry = ropeDistance(from, d) + SIX_PAST_ROPE;
    return airPath(from, { x: from.x + d.x * carry, y: BALL_RADIUS, z: from.z + d.z * carry }, 3.9);
  };
  const { points, angle } = chooseGap(from, shot, line, field, random, build);
  const landing = points[points.length - 1];
  const { index } = nearestFielder(field, landing);
  const target = towardsRope(field[index], landing);
  const run = Math.hypot(target.x - field[index].x, target.z - field[index].z);
  return plan("six", points, { angle, landing, fielder: index, action: "chase", target, arriveT: REACT + run / FIELDER_SPEED });
}

/** A chasing fielder stops short of the rope. */
function towardsRope(f, p) {
  const r = Math.hypot(p.x, p.z);
  const inside = r > BOUNDARY - 1.5 ? (BOUNDARY - 1.5) / r : 1;
  return { x: p.x * inside, z: p.z * inside };
}

function planFour(from, shot, line, field, random) {
  const build = (d) => groundPath(from, d, ropeDistance(from, d) + 0.6, 34, 8);
  const { points, angle } = chooseGap(from, shot, line, field, random, build);
  const landing = points[points.length - 1];
  const { index } = nearestFielder(field, landing);
  const target = towardsRope(field[index], landing);
  const run = Math.hypot(target.x - field[index].x, target.z - field[index].z);
  return plan("four", points, { angle, landing, fielder: index, action: "chase", target, arriveT: REACT + run / FIELDER_SPEED });
}

function planGround(from, shot, outcome, line, field, random) {
  const spec = GROUND[outcome] ?? GROUND[1];
  const wanted = between(random, spec.band);
  const build = (d) => groundPath(from, d, Math.min(wanted, ropeDistance(from, d) - 7), spec.v0, spec.v1);
  const { points: rolling, angle } = chooseGap(from, shot, line, field, random, build, 0.8);
  const stop = rolling[rolling.length - 1];
  // A quiet defensive push stays near the bat and nobody needs to run for it.
  if (outcome === "dot" && shot === "defend") {
    const d = direction(angle);
    return plan("dot", groundPath(from, d, 2.5 + 3 * random(), 8, 0), { angle });
  }
  const { index, distance } = nearestFielder(field, stop);
  // He stops just short of the ball, so his hands reach it, then turns and throws at the stumps.
  const home = field[index];
  const reach = Math.min(PICKUP_REACH, distance);
  const target = { x: stop.x + ((home.x - stop.x) / (distance || 1)) * reach, z: stop.z + ((home.z - stop.z) / (distance || 1)) * reach };
  const arriveT = REACT + Math.max(distance - reach, 0) / FIELDER_SPEED;
  const pickup = Math.max(arriveT + FIELD_CLIP.pickup, stop.t);
  const toStumps = Math.hypot(STUMPS.x - target.x, STUMPS.z - target.z) || 1;
  const hold = { ...stop, t: pickup };
  const release = {
    x: target.x + ((STUMPS.x - target.x) / toStumps) * 0.4, y: RELEASE_HEIGHT,
    z: target.z + ((STUMPS.z - target.z) / toStumps) * 0.4, t: pickup + THROW_WINDUP,
  };
  const flight = Math.max(Math.hypot(STUMPS.x - release.x, STUMPS.z - release.z) / THROW_SPEED, 0.35);
  const points = [...rolling, hold, release, ...airPath(release, STUMPS, flight, release.t).slice(1)];
  return plan(outcome === "run_out" ? "run_out" : "fielded", points, {
    angle, fielder: index, action: "field", target, arriveT,
    throwAt: pickup, releaseAt: release.t, stumpsAt: outcome === "run_out" ? release.t + flight : null,
  });
}

/**
 * The ball's whole journey after the bat, or null when it is not hit.
 * `from` is the contact point; `delivery` supplies the line and the field for pace or spin.
 */
export function planHit({ from, shot, outcome, delivery, random }) {
  if (shot === "leave" || outcome === "lbw" || outcome === "stumped") return null;
  const start = { x: from.x, y: from.y, z: from.z };
  if (outcome === "bowled") {
    const points = [{ t: 0, ...start }, { t: 0.14, x: 0, y: 0.4, z: -PITCH_HALF }];
    return plan("bowled", points, { stumpsAt: 0.14 });
  }
  const field = FIELDS[delivery.bowl_type];
  const { line } = delivery;
  if (outcome === "caught") return planCatch(start, shot, line, field, random);
  if (outcome === "6") return planSix(start, shot, line, field, random);
  if (outcome === "4") return planFour(start, shot, line, field, random);
  return planGround(start, shot, outcome, line, field, random);
}

const BATTER = { x: 0, z: -9 };
const headingTo = (from, to) => Math.atan2(to.x - from.x, to.z - from.z);
function turnBetween(a, b, f) {
  const d = Math.atan2(Math.sin(b - a), Math.cos(b - a));
  return a + d * f;
}

/**
 * Where every fielder is `after` seconds past contact, and which clip they play.
 * Heading is a rotation about y. `clip` is idle, crouch, run, catch or field, with `clipTime`
 * in seconds into it. `action` (catch or throw) is a simpler cue for the capsule fallback.
 */
export function fielderStates(hit, field, after, ballAt) {
  const look = ballAt ?? BATTER;
  return field.map((home, i) => {
    const rest = i < 2 ? "crouch" : "idle"; // The keeper and slip crouch.
    if (!hit || hit.fielder !== i || !hit.target || after <= REACT) {
      return { x: home.x, z: home.z, heading: headingTo(home, look), running: false, action: null, clip: rest, clipTime: after };
    }
    const run = Math.hypot(hit.target.x - home.x, hit.target.z - home.z);
    const span = Math.max(hit.arriveT - REACT, 1e-3);
    const clock = hit.action === "chase" ? Math.min(after, hit.end) : after;
    const f = clamp01((clock - REACT) / span);
    const x = home.x + (hit.target.x - home.x) * f;
    const z = home.z + (hit.target.z - home.z) * f;
    const at = { x, z };
    const moving = f < 1 && run > 0.2 && (hit.action !== "chase" || after < hit.end);
    const state = {
      x, z, running: moving, action: null,
      heading: moving ? headingTo(home, hit.target) : headingTo(at, look),
      clip: moving ? "run" : rest === "crouch" && f === 0 ? "crouch" : "idle",
      clipTime: moving ? (f * run) / FIELDER_SPEED : after,
    };
    if (hit.action === "catch" && after >= hit.end - FIELD_CLIP.catchReach) {
      Object.assign(state, { clip: "catch", clipTime: after - (hit.end - FIELD_CLIP.catchReach), heading: headingTo(at, BATTER), running: false });
      state.action = "catch";
    } else if (hit.action === "field" && after >= hit.throwAt - FIELD_CLIP.pickup) {
      const into = after - (hit.throwAt - FIELD_CLIP.pickup);
      const facing = turnBetween(headingTo(home, hit.target), headingTo(at, STUMPS), clamp01((after - hit.throwAt) / 0.25));
      Object.assign(state, { clip: "field", clipTime: into, heading: facing, running: false });
      state.action = after >= hit.throwAt ? "throw" : null;
    }
    return state;
  });
}

/** The moments a fielder's hands are pulled onto the ball, as [start, full, end] seconds past contact. */
export function handWindow(hit) {
  if (!hit) return null;
  if (hit.action === "catch") return [hit.end - 0.28, hit.end, hit.end + 0.3];
  if (hit.action === "field") return [hit.throwAt - 0.15, hit.throwAt, hit.throwAt + 0.15];
  return null;
}

/** Whether the ball is in a fielder's hands at this moment, and which hands hold it. */
export function heldBy(hit, after) {
  if (!hit) return null;
  if (hit.action === "catch" && after >= hit.end) return "both";
  if (hit.action === "field" && after >= hit.throwAt && after < hit.releaseAt) return "right";
  return null;
}

/** Ball position `after` seconds past contact. */
export const hitPoint = (hit, after) => sampleAt(hit.points, after);

// Camera cuts, as plain numbers so they can be tested. Each cut has an id; a new id is a hard cut.
const cut = (id, position, target, fov) => ({ id, position, target, fov });

/** The live camera after contact, or null to stay on the normal broadcast view. */
export function liveCut(hit, after, ball) {
  if (!hit || after < 0.35) return null;
  if (hit.kind === "bowled" || hit.kind === "dot") return null;
  if (hit.kind === "run_out" && after >= hit.throwAt) {
    return cut("stumps", { x: -4.6, y: 1.25, z: -6.6 }, { x: 0, y: 0.5, z: -PITCH_HALF }, 30);
  }
  if ((hit.kind === "four" || hit.kind === "six") && after >= hit.end - 1.1) {
    // Inside the rope, off to one side. A six is framed on where it lands so it drops into view.
    const p = hit.landing;
    const r = Math.hypot(p.x, p.z) || 1;
    const position = { x: (p.x / r) * 50 + (p.z / r) * 12, y: 4.5, z: (p.z / r) * 50 - (p.x / r) * 12 };
    const aim = hit.kind === "six" ? { x: (p.x / r) * BOUNDARY, y: 4, z: (p.z / r) * BOUNDARY } : ball;
    return cut("rope", position, aim, hit.kind === "six" ? 50 : 40);
  }
  if (hit.kind === "caught" && after >= hit.end - 0.9) {
    const f = hit.target;
    const r = Math.hypot(f.x, f.z + 9) || 1;
    return cut("catch", { x: f.x - (f.x / r) * 9 + 2.5, y: 2.4, z: f.z - ((f.z + 9) / r) * 9 }, { x: f.x, y: 1.3, z: f.z }, 34);
  }
  const first = hit.points[hit.points.length - 1];
  const dx = first.x;
  const dz = first.z + 9;
  const r = Math.hypot(dx, dz) || 1;
  // Behind the batter and looking along the shot, so the ball runs away towards the fielders.
  return cut("follow", { x: (-dx / r) * 20, y: 7.5, z: -9 - (dz / r) * 20 }, { x: ball.x, y: Math.max(ball.y, 1), z: ball.z }, 48);
}

/** Replays are shown for boundaries and wickets. */
export const wantsReplay = (result) => result.isWicket || result.outcome === "4" || result.outcome === "6";

/** Slow through the contact, then close to real speed while the ball travels. */
export const replayRate = (after) => (after < 0.45 ? 0.3 : 0.85);

/** Seconds past contact at which a replay ends. */
export function replayEnd(hit) {
  if (!hit) return 0.9;
  if (hit.kind === "caught" || hit.kind === "run_out") return hit.stumpsAt ?? hit.end + 0.3;
  return Math.min(hit.end + 0.3, 2.2);
}

/** Replay camera: side-on at the bat, then following a ball that travels. */
export function replayCut(hit, after, ball) {
  if (!hit || after < 0.3 || hit.kind === "bowled" || hit.kind === "dot") {
    return cut("replay-bat", { x: -5.6, y: 1.15, z: -7.4 }, { x: 0.1, y: 0.75, z: -9.2 }, 30);
  }
  return cut("replay-follow", { x: ball.x * 0.45 - 7, y: 6 + ball.y * 0.35, z: ball.z * 0.45 - 12 }, ball, 40);
}
