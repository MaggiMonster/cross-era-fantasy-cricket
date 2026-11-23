import assert from "node:assert/strict";
import test from "node:test";
import { SHOTS } from "../src/controls.js";
import { clipFor, plantedFoot } from "../src/shots.js";

test("short balls use back-foot versions and full balls front-foot versions", () => {
  assert.equal(clipFor("defend", "bouncer"), "defend_back");
  assert.equal(clipFor("drive", "short"), "drive_back");
  assert.equal(clipFor("cut", "full"), "cut_front");
  assert.equal(clipFor("pull", "yorker"), "pull_front");
  assert.equal(clipFor("drive", "full"), "drive");
  assert.equal(clipFor("cut", "short"), "cut");
});

test("every shot has a clip for every length", () => {
  for (const shot of SHOTS) for (const length of ["yorker", "full", "good", "short", "bouncer"]) {
    assert.ok(clipFor(shot, length).startsWith(shot));
  }
});

test("the back foot stays planted on front-foot shots, and the front foot on back-foot shots", () => {
  assert.equal(plantedFoot("drive"), "r");
  assert.equal(plantedFoot("cut_front"), "r");
  assert.equal(plantedFoot("pull"), "l");
  assert.equal(plantedFoot("defend_back"), "l");
});
