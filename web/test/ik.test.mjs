import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import { moveWorld, reachFraction, reachTo } from "../src/scene/ik.js";

function arm() {
  const root = new THREE.Group();
  root.position.set(1, 2, -3);
  root.rotation.set(0.3, -1.1, 0.5);
  const upper = new THREE.Object3D();
  const lower = new THREE.Object3D();
  const hand = new THREE.Object3D();
  lower.position.set(0, -0.3, 0.02);
  hand.position.set(0, -0.26, -0.03);
  hand.rotation.set(0.4, 0.2, -0.7);
  root.add(upper);
  upper.add(lower);
  lower.add(hand);
  root.updateMatrixWorld(true);
  return { root, upper, lower, hand };
}

test("the wrist reaches a target and the hand keeps its world rotation", () => {
  const { upper, lower, hand } = arm();
  const before = hand.getWorldQuaternion(new THREE.Quaternion());
  const target = hand.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0.12, 0.16, -0.09));
  reachTo(upper, lower, hand, target);
  assert.ok(hand.getWorldPosition(new THREE.Vector3()).distanceTo(target) < 1e-4);
  assert.ok(Math.abs(hand.getWorldQuaternion(new THREE.Quaternion()).dot(before)) > 0.99999);
});

test("bone lengths do not change", () => {
  const { upper, lower, hand } = arm();
  const target = hand.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(-0.1, 0.2, 0.1));
  reachTo(upper, lower, hand, target);
  const [a, b, c] = [upper, lower, hand].map((bone) => bone.getWorldPosition(new THREE.Vector3()));
  assert.ok(Math.abs(a.distanceTo(b) - Math.hypot(0.3, 0.02)) < 1e-6);
  assert.ok(Math.abs(b.distanceTo(c) - Math.hypot(0.26, 0.03)) < 1e-6);
});

test("reachFraction stops an offset at the edge of the reach", () => {
  const origin = new THREE.Vector3();
  const point = new THREE.Vector3(0.3, 0, 0);
  assert.ok(Math.abs(reachFraction(origin, point, new THREE.Vector3(0.4, 0, 0), 0.5) - 0.5) < 1e-9);
  assert.equal(reachFraction(origin, point, new THREE.Vector3(0.1, 0, 0), 0.5), 1);
  assert.equal(reachFraction(origin, new THREE.Vector3(0.6, 0, 0), new THREE.Vector3(0.1, 0, 0), 0.5), 0);
});

test("moveWorld moves a nested object by a world offset", () => {
  const { hand } = arm();
  const before = hand.getWorldPosition(new THREE.Vector3());
  const offset = new THREE.Vector3(0.1, -0.2, 0.05);
  moveWorld(hand, offset);
  assert.ok(hand.getWorldPosition(new THREE.Vector3()).distanceTo(before.add(offset)) < 1e-9);
});
