// Batting controls. Controls only choose the shot: the networks still decide the outcome.
export const SHOTS = ["leave", "defend", "work", "drive", "cut", "pull", "sweep", "loft"];

const ARROWS = {
  ArrowUp: ["drive", "loft"],
  ArrowDown: ["defend", "sweep"],
  ArrowLeft: ["cut", "leave"],
  ArrowRight: ["work", "pull"],
};

// Bowling controls. They choose length and line: the networks still decide the batter's reply.
export const LENGTHS = ["yorker", "full", "good", "short", "bouncer"];
export const LINES = ["outside_off", "stumps", "leg"];
const LINE_KEYS = { ArrowLeft: "outside_off", ArrowDown: "stumps", ArrowUp: "stumps", ArrowRight: "leg" };

/** What a key does while bowling: { length }, { line }, { bowl: true }, or null. */
export function bowlingKey(key) {
  if (/^[1-5]$/.test(key)) return { length: LENGTHS[Number(key) - 1] };
  if (LINE_KEYS[key]) return { line: LINE_KEYS[key] };
  return key === "Enter" || key === " " ? { bowl: true } : null;
}

/** The shot for a key press, or null. Accepts number keys 1-8 and arrows, with Shift for the second shot. */
export function shotForKey(key, shift = false) {
  if (ARROWS[key]) return ARROWS[key][shift ? 1 : 0];
  const digit = /^[1-8]$/.test(key) ? Number(key) : 0;
  return digit ? SHOTS[digit - 1] : null;
}
