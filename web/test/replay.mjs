// Used by tests/test_web_sampler.py. Usage: node replay.mjs networks.json fixture.json
// Prints every probability and replayed duel as JSON, for comparison with Python.
import { readFileSync } from "node:fs";
import { Duel, Networks, mulberry32 } from "../src/model/duel.js";

const networks = new Networks(JSON.parse(readFileSync(process.argv[2], "utf8")));
const fixture = JSON.parse(readFileSync(process.argv[3], "utf8"));
const { states } = networks;

const probabilities = {};
for (const [batter, bowler] of networks.data.matchups) {
  const bowlType = networks.data.bowlers[bowler].bowl_type;
  const rows = [];
  for (const pressure of states.pressure) {
    rows.push(...networks.lengthProbs(bowler, pressure));
    for (const length of states.length) {
      for (const line of states.line) {
        const delivery = { bowl_type: bowlType, length, line };
        rows.push(...networks.shotProbs(batter, delivery, pressure));
        for (const shot of states.shot) {
          rows.push(...networks.outcomeProbs(batter, bowler, delivery, shot, pressure));
        }
      }
    }
  }
  probabilities[`${batter}-${bowler}`] = rows;
}

const duels = fixture.duels.map(({ batter, bowler, uniforms, shots }) => {
  let next = 0;
  const duel = new Duel(networks, batter, bowler, { random: () => uniforms[next++] });
  const balls = [];
  while (!duel.isOver) {
    const d = duel.nextDelivery();
    const r = duel.play(shots ? shots[balls.length] : null);
    balls.push([d.length, d.line, r.shot, r.outcome]);
  }
  return { balls, runs: duel.runs, won: duel.batterWon, used: next };
});

const winRates = {};
for (const [batter, bowler] of networks.data.matchups) {
  const random = mulberry32(20261123);
  let wins = 0;
  for (let i = 0; i < fixture.free_duels; i++) {
    const duel = new Duel(networks, batter, bowler, { random });
    while (!duel.isOver) duel.play();
    wins += duel.batterWon ? 1 : 0;
  }
  winRates[`${batter}-${bowler}`] = wins / fixture.free_duels;
}

process.stdout.write(JSON.stringify({ probabilities, duels, winRates }));
