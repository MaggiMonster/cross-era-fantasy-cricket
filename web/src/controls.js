// Batting controls. Controls only choose the shot: the networks still decide the outcome.
export const SHOTS = ["leave", "defend", "work", "drive", "cut", "pull", "sweep", "loft"];

const ARROWS = {
  ArrowUp: ["drive", "loft"],
  ArrowDown: ["defend", "sweep"],
  ArrowLeft: ["cut", "leave"],
  ArrowRight: ["work", "pull"],
};

/** The shot for a key press, or null. Accepts number keys 1-8 and arrows, with Shift for the second shot. */
export function shotForKey(key, shift = false) {
  if (ARROWS[key]) return ARROWS[key][shift ? 1 : 0];
  const digit = /^[1-8]$/.test(key) ? Number(key) : 0;
  return digit ? SHOTS[digit - 1] : null;
}
