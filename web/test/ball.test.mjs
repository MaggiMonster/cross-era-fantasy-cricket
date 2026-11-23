import assert from "node:assert/strict";
import { test } from "node:test";
import { BOWLERS, POPPING_Z, deliveryPath, placeholderHit, sampleAt } from "../src/sim/ball.js";

const LENGTHS = ["yorker", "full", "good", "short", "bouncer"];
const LINES = ["outside_off", "stumps", "leg"];
const TYPES = { bumrah: "pace", warne: "spin" };
const path = (bowler, length, line = "stumps") => deliveryPath(bowler, { bowl_type: TYPES[bowler], length, line });

for (const bowler of Object.keys(BOWLERS)) {
  test(`${bowler}: every delivery pitches on its length and reaches its line`, () => {
    for (const length of LENGTHS) {
      for (const line of LINES) {
        const p = path(bowler, length, line);
        assert.ok(Math.abs(p.bounce.z - p.targetZ) < 0.02, `${length} ${line} pitched at ${p.bounce.z}`);
        assert.ok(Math.abs(p.crease.x - p.targetX) < 0.02, `${length} ${line} arrived at ${p.crease.x}`);
      }
    }
  });

  test(`${bowler}: shorter balls pitch further from the batter and arrive higher`, () => {
    const paths = LENGTHS.map((l) => path(bowler, l));
    for (let i = 1; i < paths.length; i++) {
      assert.ok(paths[i].bounce.z > paths[i - 1].bounce.z);
      assert.ok(paths[i].crease.y > paths[i - 1].crease.y, `${LENGTHS[i]} should arrive higher`);
    }
  });
}

test("Bumrah's bouncer reaches at least chest height", () => {
  assert.ok(path("bumrah", "bouncer").crease.y > 1.25);
});

test("pace reaches the batter much sooner than spin", () => {
  assert.ok(path("bumrah", "good").crease.t < 0.55);
  assert.ok(path("warne", "good").crease.t > 0.7);
});

test("Warne's leg-break turns towards off after pitching, Bumrah's barely moves", () => {
  const sideways = (p) => {
    const after = p.points.find((q) => q.t > p.bounce.t + 0.1);
    return (after.x - p.bounce.x) / (after.t - p.bounce.t);
  };
  assert.ok(sideways(path("warne", "good")) < -1);
  assert.ok(Math.abs(sideways(path("bumrah", "good"))) < 1);
});

test("sampling interpolates along the path", () => {
  const p = path("bumrah", "good");
  const q = sampleAt(p.points, p.crease.t);
  assert.ok(Math.abs(q.z - POPPING_Z) < 0.1);
});

test("placeholder hit: bowled reaches the stumps, a leave is not hit", () => {
  const from = { x: 0.2, y: 0.5, z: POPPING_Z };
  assert.equal(placeholderHit(from, "leave", "dot"), null);
  assert.equal(placeholderHit(from, "drive", "bowled").at(-1).z, -10.06);
});
