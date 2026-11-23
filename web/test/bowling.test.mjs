import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { bowlingKey, LENGTHS, LINES } from "../src/controls.js";
import { Duel, Networks } from "../src/model/duel.js";

const networks = new Networks(JSON.parse(readFileSync(new URL("../public/data/networks.json", import.meta.url))));

test("bowling keys choose every length and line, and bowl", () => {
  LENGTHS.forEach((length, i) => assert.deepEqual(bowlingKey(String(i + 1)), { length }));
  assert.deepEqual(bowlingKey("ArrowLeft"), { line: "outside_off" });
  assert.deepEqual(bowlingKey("ArrowDown"), { line: "stumps" });
  assert.deepEqual(bowlingKey("ArrowRight"), { line: "leg" });
  assert.deepEqual(bowlingKey("Enter"), { bowl: true });
  assert.deepEqual(bowlingKey(" "), { bowl: true });
  assert.equal(bowlingKey("6"), null);
});

test("a chosen delivery uses no random numbers and keeps the bowler's type", () => {
  for (const [batter, bowler] of networks.data.matchups) {
    let draws = 0;
    const duel = new Duel(networks, batter, bowler, { random: () => { draws += 1; return 0.5; } });
    for (const length of LENGTHS) {
      for (const line of LINES) {
        const delivery = duel.chooseDelivery(length, line);
        assert.deepEqual(delivery, { bowl_type: networks.data.bowlers[bowler].bowl_type, length, line });
      }
    }
    assert.equal(draws, 0);
  }
});

test("after a chosen delivery, the networks draw exactly the shot and the outcome", () => {
  const [batter, bowler] = networks.data.matchups[0];
  const uniforms = [0.31, 0.77];
  let next = 0;
  const duel = new Duel(networks, batter, bowler, { random: () => uniforms[next++] });
  const delivery = duel.chooseDelivery("good", "stumps");
  const pressure = duel.pressure;
  const { states } = networks;
  const pick = (probs, u) => {
    let total = 0;
    for (let i = 0; i < probs.length; i++) {
      total += probs[i];
      if (u < total) return i;
    }
    return probs.length - 1;
  };
  const shot = states.shot[pick(networks.shotProbs(batter, delivery, pressure), uniforms[0])];
  const outcome = states.outcome[pick(networks.outcomeProbs(batter, bowler, delivery, shot, pressure), uniforms[1])];
  const result = duel.play(null);
  assert.equal(next, 2);
  assert.equal(result.shot, shot);
  assert.equal(result.outcome, outcome);
});

test("an unknown length or line is refused", () => {
  const [batter, bowler] = networks.data.matchups[0];
  const duel = new Duel(networks, batter, bowler, { random: () => 0.5 });
  assert.throws(() => duel.chooseDelivery("beamer", "stumps"));
  assert.throws(() => duel.chooseDelivery("good", "wide"));
});
