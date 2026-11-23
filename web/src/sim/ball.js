// Ball flight for each delivery. No Three.js here, so Node can test it.
// Metres and seconds. x: + is leg side for a right-hander (viewer's right from behind the
// bowler). y: up. z: stumps at +10.06 (bowler) and -10.06 (striker).
// Physics is presentation only: the networks have already decided the ball.

export const PITCH_HALF = 10.06;
export const POPPING_Z = -8.84;
export const BALL_RADIUS = 0.036;

const GRAVITY = 9.81;
// 0.5 * air density * drag coefficient * area / mass for a cricket ball.
const DRAG = 0.007;
const DT = 1 / 480;

// Distance from the striker's stumps at which each length pitches.
const PITCH_DISTANCE = {
  pace: { yorker: 1.2, full: 3.4, good: 6.4, short: 8.6, bouncer: 11.0 },
  spin: { yorker: 1.0, full: 2.5, good: 3.8, short: 4.9, bouncer: 6.0 },
};
// Where the ball should cross the batter's crease, sideways.
const LINE_X = { outside_off: -0.36, stumps: -0.02, leg: 0.24 };

// Bowler styles. `turn` is sideways speed added at the bounce (negative: leg to off).
export const BOWLERS = {
  bumrah: { speed: 39.5, releaseHeight: 2.12, releaseX: -0.42, swing: -0.9, turn: 0.12, restitution: 0.58, grip: 0.86, dip: 0 },
  warne: { speed: 22.5, releaseHeight: 1.86, releaseX: -0.3, swing: 0.25, turn: -2.1, restitution: 0.56, grip: 0.8, dip: 1.7 },
};

function step(s, style, bounced) {
  const speed = Math.hypot(s.vx, s.vy, s.vz);
  const ax = -DRAG * speed * s.vx + (bounced ? 0 : style.swing);
  const ay = -GRAVITY - DRAG * speed * s.vy - (bounced ? 0 : style.dip);
  const az = -DRAG * speed * s.vz;
  s.vx += ax * DT;
  s.vy += ay * DT;
  s.vz += az * DT;
  s.x += s.vx * DT;
  s.y += s.vy * DT;
  s.z += s.vz * DT;
  s.t += DT;
}

/** Fly to the first bounce, then past the batter. Returns the path and key points. */
function fly(release, velocity, style) {
  const s = { ...release, ...velocity, t: 0 };
  const points = [{ t: 0, x: s.x, y: s.y, z: s.z }];
  let bounce = null;
  let crease = null;
  let n = 0;
  while (s.z > -PITCH_HALF - 3.5 && s.t < 3) {
    const before = { x: s.x, y: s.y, z: s.z, t: s.t };
    step(s, style, bounce !== null);
    // One step is up to 8 cm at pace, so key points are interpolated to their exact position.
    if (crease === null && s.z <= POPPING_Z) {
      const f = (before.z - POPPING_Z) / (before.z - s.z);
      crease = { t: before.t + (s.t - before.t) * f, x: before.x + (s.x - before.x) * f, y: before.y + (s.y - before.y) * f, z: POPPING_Z };
    }
    if (bounce === null && s.y <= BALL_RADIUS) {
      const f = (before.y - BALL_RADIUS) / (before.y - s.y);
      s.x = before.x + (s.x - before.x) * f;
      s.z = before.z + (s.z - before.z) * f;
      s.t = before.t + (s.t - before.t) * f;
      s.y = BALL_RADIUS;
      bounce = { t: s.t, x: s.x, y: s.y, z: s.z };
      s.vy = -s.vy * style.restitution;
      s.vx = s.vx * style.grip + style.turn;
      s.vz *= style.grip;
    } else if (bounce !== null && s.y <= BALL_RADIUS && s.vy < 0) {
      s.y = BALL_RADIUS;
      s.vy = -s.vy * 0.35;
      s.vx *= 0.8;
      s.vz *= 0.8;
    }
    if (++n % 4 === 0) points.push({ t: s.t, x: s.x, y: s.y, z: s.z });
  }
  return { points, bounce, crease };
}

/**
 * Solve the release so the ball pitches on the delivery's length and reaches its line.
 * `jitter` is optional visual variation, from a generator separate from the model's.
 */
export function deliveryPath(bowler, delivery, jitter = { speed: 0, length: 0, line: 0 }) {
  const style = BOWLERS[bowler];
  if (!style) throw new Error(`unknown bowler ${bowler}`);
  const distance = PITCH_DISTANCE[delivery.bowl_type][delivery.length] + jitter.length;
  const targetZ = -PITCH_HALF + distance;
  const targetX = LINE_X[delivery.line] + jitter.line;
  const speed = style.speed + jitter.speed;
  const release = { x: style.releaseX, y: style.releaseHeight, z: 8.9 };

  const launch = (vx, vy) => fly(release, { vx, vy, vz: -Math.sqrt(Math.max(speed * speed - vx * vx - vy * vy, 1)) }, style);

  // More upward speed always pitches the ball further down the wicket, so bisect on it.
  const solveLength = (vx) => {
    let low = -14;
    let high = 8;
    for (let i = 0; i < 26; i++) {
      const vy = (low + high) / 2;
      const { bounce } = launch(vx, vy);
      if (!bounce || bounce.z < targetZ) high = vy;
      else low = vy;
    }
    return launch(vx, (low + high) / 2);
  };

  // Crease position is close to linear in sideways speed, so a secant search converges fast.
  let vx0 = (targetX - release.x) / ((release.z - POPPING_Z) / speed);
  let path0 = solveLength(vx0);
  let vx1 = vx0 + (targetX - path0.crease.x) * (speed / (release.z - POPPING_Z));
  let path = solveLength(vx1);
  for (let i = 0; i < 8 && Math.abs(path.crease.x - targetX) > 0.002; i++) {
    const slope = (path.crease.x - path0.crease.x) / (vx1 - vx0);
    if (!Number.isFinite(slope) || slope === 0) break;
    [vx0, path0] = [vx1, path];
    vx1 += (targetX - path.crease.x) / slope;
    path = solveLength(vx1);
  }
  return { ...path, release, targetZ, targetX, speed };
}

/** Position at time t, interpolated along a path. */
export function sampleAt(points, t) {
  if (t <= points[0].t) return points[0];
  const last = points[points.length - 1];
  if (t >= last.t) return last;
  let lo = 0;
  let hi = points.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (points[mid].t <= t) lo = mid;
    else hi = mid;
  }
  const a = points[lo];
  const b = points[hi];
  const f = (t - a.t) / (b.t - a.t);
  return { t, x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, z: a.z + (b.z - a.z) * f };
}

/** Where and when the ball first reaches depth z, or null if it never does. */
export function pointAtZ(points, z) {
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    if (a.z >= z && b.z <= z) {
      const f = a.z === b.z ? 0 : (a.z - z) / (a.z - b.z);
      return { t: a.t + (b.t - a.t) * f, x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, z };
    }
  }
  return null;
}

/**
 * The moment the ball passes closest to a straight blade from `a` to `b`.
 * Returns the ball's position and time, and the nearest point on the blade.
 */
export function closestToBlade(points, a, b, minZ = -10, maxZ = -7.4) {
  const ux = b.x - a.x;
  const uy = b.y - a.y;
  const uz = b.z - a.z;
  const lengthSq = ux * ux + uy * uy + uz * uz;
  let best = null;
  for (const p of points) {
    if (p.z < minZ || p.z > maxZ) continue;
    const f = Math.min(Math.max(((p.x - a.x) * ux + (p.y - a.y) * uy + (p.z - a.z) * uz) / lengthSq, 0), 1);
    const blade = { x: a.x + ux * f, y: a.y + uy * f, z: a.z + uz * f };
    const distance = Math.hypot(p.x - blade.x, p.y - blade.y, p.z - blade.z);
    if (!best || distance < best.distance) best = { ball: { t: p.t, x: p.x, y: p.y, z: p.z }, blade, distance };
  }
  return best;
}

// Placeholder direction for each shot (radians, 0 straight back past the bowler, + leg side).
// Turn 7 replaces this with direction and distance driven by shot plus outcome.
const SHOT_ANGLE = { defend: 0.1, work: 1.1, drive: -0.35, cut: -1.75, pull: 1.75, sweep: 2.1, loft: 0.15, leave: 0 };
const OUTCOME_DISTANCE = { dot: 7, 1: 26, 2: 42, 3: 56, 4: 72, 6: 88, caught: 40 };

/** Placeholder path after the bat. Returns null when the ball is not hit. */
export function placeholderHit(from, shot, outcome) {
  if (shot === "leave" || outcome === "lbw" || outcome === "stumped") return null;
  if (outcome === "bowled") {
    const dt = 0.14;
    return [{ t: 0, ...xyz(from) }, { t: dt, x: 0, y: 0.4, z: -PITCH_HALF }];
  }
  const distance = OUTCOME_DISTANCE[outcome] ?? 18;
  const angle = SHOT_ANGLE[shot] ?? 0;
  const aerial = outcome === "6" || outcome === "caught";
  const duration = aerial ? 3 : Math.max(0.7, distance / 24);
  const apex = aerial ? distance * 0.3 : 0.25;
  const points = [];
  for (let i = 0; i <= 60; i++) {
    const f = i / 60;
    const reach = aerial ? f : 1 - (1 - f) * (1 - f);
    points.push({
      t: f * duration,
      x: from.x + Math.sin(angle) * distance * reach,
      y: Math.max(BALL_RADIUS, from.y * (1 - f) + 4 * apex * f * (1 - f)),
      z: from.z + Math.cos(angle) * distance * reach,
    });
  }
  return points;
}

function xyz({ x, y, z }) {
  return { x, y, z };
}
