import assert from "node:assert/strict";
import { test } from "node:test";
import { BALL_RADIUS, POPPING_Z } from "../src/sim/ball.js";
import { mulberry32 as mulberry32Free } from "../src/model/duel.js";
import { BOUNDARY, FIELD_CLIP, FIELDS, FIELDER_SPEED, REACT, SECTORS, fielderStates, heldBy, liveCut, planHit, replayCut, replayEnd, ropeDistance, wantsReplay } from "../src/sim/hit.js";

const from = { x: 0.1, y: 0.6, z: POPPING_Z };
const SHOTS = ["defend", "work", "drive", "cut", "pull", "sweep", "loft"];
const LINES = ["outside_off", "stumps", "leg"];
const TYPES = ["pace", "spin"];
const radius = (p) => Math.hypot(p.x, p.z);

function* cases(outcome, seeds = 12) {
  for (const bowl_type of TYPES) for (const line of LINES) for (const shot of SHOTS) for (let seed = 1; seed <= seeds; seed++) {
    const delivery = { bowl_type, length: "good", line };
    yield { delivery, shot, hit: planHit({ from, shot, outcome, delivery, random: mulberry32Free(seed) }) };
  }
}

test("a leave, lbw and stumping are not hit", () => {
  const delivery = { bowl_type: "pace", length: "good", line: "stumps" };
  const random = mulberry32Free(1);
  assert.equal(planHit({ from, shot: "leave", outcome: "dot", delivery, random }), null);
  assert.equal(planHit({ from, shot: "drive", outcome: "lbw", delivery, random }), null);
  assert.equal(planHit({ from, shot: "drive", outcome: "stumped", delivery, random }), null);
});

test("bowled reaches the stumps", () => {
  const delivery = { bowl_type: "pace", length: "good", line: "stumps" };
  const hit = planHit({ from, shot: "drive", outcome: "bowled", delivery, random: mulberry32Free(1) });
  assert.equal(hit.points.at(-1).z, -10.06);
});

test("a four crosses the rope along the ground and no fielder can reach it", () => {
  for (const { hit, delivery } of cases("4")) {
    assert.ok(radius(hit.points.at(-1)) >= BOUNDARY, "did not reach the rope");
    assert.ok(hit.points.slice(30).every((p) => p.y < 0.2), "a four must stay on the ground");
    for (const p of hit.points) {
      for (const f of FIELDS[delivery.bowl_type]) {
        assert.ok(Math.hypot(p.x - f.x, p.z - f.z) > FIELDER_SPEED * Math.max(p.t - REACT, 0), `${f.name} reaches a four`);
      }
    }
  }
});

test("a six lands beyond the rope and is above head height at the rope", () => {
  for (const { hit } of cases("6")) {
    assert.ok(radius(hit.points.at(-1)) > BOUNDARY);
    const atRope = hit.points.find((p) => radius(p) >= BOUNDARY);
    assert.ok(atRope.y > 3, `only ${atRope.y} m high at the rope`);
  }
});

test("more runs travel further, and everything stays inside the rope", () => {
  const stop = (hit) => Math.max(...hit.points.map((p) => Math.hypot(p.x - from.x, p.z - from.z)));
  for (const shot of ["drive", "pull", "cut"]) {
    const delivery = { bowl_type: "pace", length: "good", line: "stumps" };
    const far = ["1", "2", "3"].map((outcome) => stop(planHit({ from, shot, outcome, delivery, random: mulberry32Free(3) })));
    assert.ok(far[0] < far[1] && far[1] < far[2], `${shot}: ${far}`);
  }
  for (const outcome of ["dot", "1", "2", "3", "run_out"]) {
    for (const { hit } of cases(outcome, 4)) assert.ok(hit.points.every((p) => radius(p) < BOUNDARY), outcome);
  }
});

test("a catch ends in a fielder's hands, and they can get there in time", () => {
  for (const { hit, delivery } of cases("caught")) {
    const end = hit.points.at(-1);
    const f = FIELDS[delivery.bowl_type][hit.fielder];
    assert.ok(Math.hypot(end.x - hit.hands.x, end.z - hit.hands.z) < 1e-6);
    const runs = Math.hypot(hit.target.x - f.x, hit.target.z - f.z) > 0.01;
    if (runs) assert.ok(hit.arriveT <= hit.end - FIELD_CLIP.catchReach, `${f.name} arrives late`);
    const state = fielderStates(hit, FIELDS[delivery.bowl_type], hit.end, end)[hit.fielder];
    const gap = Math.hypot(state.x - end.x, state.z - end.z);
    assert.ok(Math.abs(gap - 0.45) < 0.01, `hands should be just in front of the body, got ${gap}`);
    assert.equal(state.clip, "catch");
    assert.ok(Math.abs(state.clipTime - FIELD_CLIP.catchReach) < 1e-9, "the hands meet the ball on the clip's reach frame");
    assert.equal(heldBy(hit, hit.end), "both");
  }
});

test("a fielder stops just short of the ball, picks it up and throws from his hand", () => {
  for (const { hit, delivery } of cases("2", 3)) {
    const field = FIELDS[delivery.bowl_type];
    const stop = hit.points[60];
    const at = fielderStates(hit, field, hit.throwAt, stop)[hit.fielder];
    assert.ok(Math.hypot(at.x - stop.x, at.z - stop.z) <= 0.56, "the ball should be within reach");
    assert.equal(at.clip, "field");
    assert.ok(Math.abs(at.clipTime - FIELD_CLIP.pickup) < 1e-9);
    assert.equal(heldBy(hit, hit.throwAt + 0.1), "right");
    assert.equal(heldBy(hit, hit.releaseAt + 0.01), null);
    const before = fielderStates(hit, field, hit.throwAt - FIELD_CLIP.pickup - 0.01, stop)[hit.fielder];
    assert.notEqual(before.clip, "field");
  }
});

test("running fielders play the run clip at their real speed", () => {
  const delivery = { bowl_type: "pace", length: "good", line: "stumps" };
  const hit = planHit({ from, shot: "drive", outcome: "3", delivery, random: mulberry32Free(5) });
  const field = FIELDS.pace;
  const t = (hit.arriveT + REACT) / 2;
  const a = fielderStates(hit, field, t, from)[hit.fielder];
  const b = fielderStates(hit, field, t + 0.1, from)[hit.fielder];
  assert.equal(a.clip, "run");
  assert.ok(Math.abs((b.clipTime - a.clipTime) - 0.1) < 1e-9, "7 m/s in the game is 7 m/s in the clip");
  assert.deepEqual(fielderStates(null, field, 0).map((s) => s.clip).slice(0, 3), ["crouch", "crouch", "idle"]);
});

test("a fielded ball goes back to the stumps, and a run out breaks them when it arrives", () => {
  for (const { hit } of cases("run_out", 3)) {
    const end = hit.points.at(-1);
    assert.ok(Math.abs(end.z + 10.06) < 1e-6 && Math.abs(end.x) < 1e-6);
    assert.ok(Math.abs(hit.stumpsAt - hit.end) < 1e-6);
  }
});

test("path times never run backwards", () => {
  for (const outcome of ["dot", "1", "2", "3", "4", "6", "caught", "run_out"]) {
    for (const { hit } of cases(outcome, 2)) {
      for (let i = 1; i < hit.points.length; i++) assert.ok(hit.points[i].t >= hit.points[i - 1].t, outcome);
    }
  }
});

test("the same visual seed gives the same path", () => {
  const delivery = { bowl_type: "spin", length: "full", line: "leg" };
  const make = () => planHit({ from, shot: "loft", outcome: "6", delivery, random: mulberry32Free(9) });
  assert.deepEqual(make().points, make().points);
});

test("every shot has an arc, and rope distance is right from the centre", () => {
  for (const shot of [...SHOTS, "leave"]) assert.ok(SECTORS[shot]);
  assert.ok(Math.abs(ropeDistance({ x: 0, z: 0 }, { x: 1, z: 0 }) - BOUNDARY) < 1e-9);
  assert.ok(BALL_RADIUS > 0);
});

test("camera cuts and replays cover boundaries and wickets", () => {
  const delivery = { bowl_type: "pace", length: "good", line: "stumps" };
  const four = planHit({ from, shot: "drive", outcome: "4", delivery, random: mulberry32Free(2) });
  assert.equal(liveCut(four, 0.1, from), null);
  assert.equal(liveCut(four, 0.6, from).id, "follow");
  assert.equal(liveCut(four, four.end, from).id, "rope");
  assert.ok(replayEnd(four) <= 2.2);
  assert.ok(replayCut(four, 0.1, from).id === "replay-bat");
  assert.ok(wantsReplay({ isWicket: true, outcome: "bowled" }));
  assert.ok(wantsReplay({ isWicket: false, outcome: "6" }));
  assert.ok(!wantsReplay({ isWicket: false, outcome: "2" }));
});
