import assert from "node:assert/strict";
import test from "node:test";
import { SHOTS, shotForKey } from "../src/controls.js";

test("number keys choose the shots in order", () => {
  SHOTS.forEach((shot, i) => assert.equal(shotForKey(String(i + 1)), shot));
});

test("arrow keys reach all eight shots exactly once", () => {
  const keys = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
  const shots = keys.flatMap((key) => [shotForKey(key), shotForKey(key, true)]);
  assert.deepEqual([...shots].sort(), [...SHOTS].sort());
});

test("other keys choose nothing", () => {
  for (const key of ["0", "9", "a", " ", "Enter"]) assert.equal(shotForKey(key), null);
});
