// The duel in JavaScript: a line-for-line port of duel/engine.py and duel/matchup.py.
// It samples the exported network tables. tests/test_web_sampler.py proves it matches Python.
// This file must not import Three.js, so Node can run it in tests.

/** Index into a row-major flat table. */
function offset(shape, index) {
  return index.reduce((acc, value, i) => acc * shape[i] + value, 0);
}

/** Same rule as numpy Generator.choice(p=...): one uniform, first cdf entry above it. */
export function choose(probs, u) {
  const cdf = new Array(probs.length);
  let total = 0;
  for (let i = 0; i < probs.length; i++) {
    total += probs[i];
    cdf[i] = total;
  }
  for (let i = 0; i < cdf.length; i++) {
    if (u < cdf[i] / total) return i;
  }
  return cdf.length - 1;
}

/** Small seeded generator for play. Tests inject Python's uniforms instead. */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class Networks {
  constructor(data) {
    this.data = data;
    this.states = data.states;
    this.n = Object.fromEntries(Object.entries(data.states).map(([k, v]) => [k, v.length]));
    this.wickets = new Set(data.wickets);
  }

  idx(axis, value) {
    const i = this.states[axis].indexOf(value);
    if (i < 0) throw new Error(`unknown ${axis}: ${value}`);
    return i;
  }

  slice(table, axes, index) {
    const shape = axes.map((a) => this.n[a]);
    const size = shape[shape.length - 1];
    const start = offset(shape.slice(0, -1), index) * size;
    return table.slice(start, start + size);
  }

  pressure(requiredRate) {
    const { medium, high } = this.data.pressure_rates;
    if (requiredRate >= high) return "high";
    return requiredRate >= medium ? "medium" : "low";
  }

  defaultTarget(batter, overs = 3) {
    return Math.floor(this.data.batters[batter].runs_per_ball * overs * 6) + 1;
  }

  lengthProbs(bowler, pressure) {
    return this.slice(this.data.bowlers[bowler].length, ["pressure", "length"], [this.idx("pressure", pressure)]);
  }

  lineProbs(bowler, length) {
    return this.slice(this.data.bowlers[bowler].line, ["length", "line"], [this.idx("length", length)]);
  }

  shotProbs(batter, delivery, pressure) {
    return this.slice(this.data.batters[batter].shot, this.data.axes["batter.shot"], [
      this.idx("pressure", pressure),
      this.idx("bowl_type", delivery.bowl_type),
      this.idx("length", delivery.length),
      this.idx("line", delivery.line),
    ]);
  }

  /** P(o) proportional to batter(o) * bowler(o) / baseline(o), all given this delivery. */
  outcomeProbs(batter, bowler, delivery, shot, pressure) {
    const p = this.idx("pressure", pressure);
    const b = this.idx("bowl_type", delivery.bowl_type);
    const l = this.idx("length", delivery.length);
    const m = this.idx("line", delivery.line);
    const { axes } = this.data;
    const bat = this.slice(this.data.batters[batter].outcome, axes["batter.outcome"], [p, this.idx("shot", shot), b, l]);
    const bowl = this.slice(this.data.bowlers[bowler].outcome, axes["bowler.outcome"], [p, l, m]);
    const base = this.slice(this.data.baseline, axes.baseline, [p, b, l, m]);
    const raw = bat.map((v, i) => (v * bowl[i]) / base[i]);
    const sum = raw.reduce((x, y) => x + y, 0);
    const probs = raw.map((v) => v / sum);
    return shot === "leave" ? this.leaveProbs(batter, delivery, pressure, probs, bowl, base) : probs;
  }

  wicketProb(probs) {
    return this.states.outcome.reduce((total, o, i) => total + (this.wickets.has(o) ? probs[i] : 0), 0);
  }

  /** A leave cannot score or be caught. Its risk depends on line and length. */
  leaveProbs(batter, delivery, pressure, p, bowl, base) {
    const { states, data } = this;
    const p_ = this.idx("pressure", pressure);
    const b = this.idx("bowl_type", delivery.bowl_type);
    const l = this.idx("length", delivery.length);
    const m = this.idx("line", delivery.line);
    const shots = this.shotProbs(batter, delivery, pressure);
    let batterWicket = 0;
    shots.forEach((weight, s) => {
      batterWicket += weight * this.wicketProb(this.slice(data.batters[batter].outcome, data.axes["batter.outcome"], [p_, s, b, l]));
    });
    const baseWicket = this.wicketProb(base);
    const [low, high] = data.leave_skill_limits;
    const skill = Math.min(Math.max((batterWicket / baseWicket) * this.wicketProb(bowl) / baseWicket, low), high);
    const prior = data.leave_risk[m * this.n.length + l];
    const odds = (prior / (1 - prior)) * skill;
    const risk = odds / (1 + odds);
    const [dot, bowled, lbw, stumped] = ["dot", "bowled", "lbw", "stumped"].map((o) => this.idx("outcome", o));
    const share = p[bowled] / (p[bowled] + p[lbw]);
    const result = new Array(states.outcome.length).fill(0);
    result[bowled] = risk * share;
    result[lbw] = risk * (1 - share);
    result[stumped] = p[stumped];
    result[dot] = 1 - risk - p[stumped];
    return result;
  }
}

export class Duel {
  /** `random` returns uniforms in [0, 1). Draw order matches duel/engine.py. */
  constructor(networks, batter, bowler, { target = null, overs = 3, lives = 3, random }) {
    if (!networks.data.matchups.some(([a, b]) => a === batter && b === bowler)) {
      throw new Error(`matchups are old vs new, got ${batter} vs ${bowler}`);
    }
    if (overs < 1 || lives < 1) throw new Error("overs and lives must be at least 1");
    this.net = networks;
    this.batter = batter;
    this.bowler = bowler;
    this.target = target ?? networks.defaultTarget(batter, overs);
    if (this.target < 1) throw new Error("target must be at least 1");
    this.overs = overs;
    this.lives = lives;
    this.runs = 0;
    this.ballsBowled = 0;
    this.livesLost = 0;
    this.random = random;
    this.delivery = null;
    this.history = [];
  }

  get ballsLeft() { return Math.max(this.overs * 6 - this.ballsBowled, 0); }
  get runsNeeded() { return Math.max(this.target - this.runs, 0); }
  get livesLeft() { return Math.max(this.lives - this.livesLost, 0); }
  get batterWon() { return this.runs >= this.target; }
  get isOver() { return this.batterWon || this.ballsLeft === 0 || this.livesLeft === 0; }

  get requiredRate() {
    if (this.runsNeeded === 0) return 0;
    if (this.ballsLeft === 0) return Infinity;
    return (this.runsNeeded * 6) / this.ballsLeft;
  }

  get pressure() { return this.net.pressure(this.requiredRate); }

  nextDelivery() {
    if (this.isOver) throw new Error("the duel is over");
    if (!this.delivery) {
      const { states, data } = this.net;
      const k = choose(this.net.lengthProbs(this.bowler, this.pressure), this.random());
      const m = choose(this.net.lineProbs(this.bowler, states.length[k]), this.random());
      this.delivery = { bowl_type: data.bowlers[this.bowler].bowl_type, length: states.length[k], line: states.line[m] };
    }
    return this.delivery;
  }

  /** Play the ball. `shot` null lets the batting network choose. */
  play(shot = null) {
    const delivery = this.nextDelivery();
    const pressure = this.pressure;
    const { states } = this.net;
    const chosen = shot ?? states.shot[choose(this.net.shotProbs(this.batter, delivery, pressure), this.random())];
    const probs = this.net.outcomeProbs(this.batter, this.bowler, delivery, chosen, pressure);
    const outcome = states.outcome[choose(probs, this.random())];
    const isWicket = this.net.wickets.has(outcome);
    this.runs += /^\d+$/.test(outcome) ? Number(outcome) : 0;
    this.ballsBowled += 1;
    this.livesLost += isWicket ? 1 : 0;
    this.delivery = null;
    const result = { delivery, shot: chosen, outcome, isWicket, pressure, runs: this.runs, balls: this.ballsBowled, livesLost: this.livesLost };
    this.history.push(result);
    return result;
  }
}
