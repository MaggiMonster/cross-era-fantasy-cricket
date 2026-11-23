// Small runtime IK, used to bring the bat to the ball's real line and height.
import * as THREE from "three";

const a = new THREE.Vector3();
const b = new THREE.Vector3();
const c = new THREE.Vector3();
const ab = new THREE.Vector3();
const bc = new THREE.Vector3();
const ac = new THREE.Vector3();
const at = new THREE.Vector3();
const axis = new THREE.Vector3();
const delta = new THREE.Quaternion();
const parentWorld = new THREE.Quaternion();
const worldRotation = new THREE.Quaternion();
const handWorld = new THREE.Quaternion();

/** Rotate a bone by `q`, expressed in world space. */
export function rotateWorld(bone, q) {
  bone.getWorldQuaternion(worldRotation);
  bone.parent.getWorldQuaternion(parentWorld);
  bone.quaternion.copy(parentWorld.clone().invert().multiply(q).multiply(worldRotation)).normalize();
  bone.updateWorldMatrix(true, true);
}

/** Move an object by a world-space offset. */
export function moveWorld(object, offset) {
  object.getWorldPosition(a).add(offset);
  object.parent.worldToLocal(a);
  object.position.copy(a);
  object.updateWorldMatrix(true, true);
}

/**
 * The largest k in [0, 1] that keeps `point + k * offset` within `reach` of `origin`.
 * Returns 0 if the point is already out of reach.
 */
export function reachFraction(origin, point, offset, reach) {
  const px = point.x - origin.x;
  const py = point.y - origin.y;
  const pz = point.z - origin.z;
  const qa = offset.lengthSq();
  const qb = 2 * (px * offset.x + py * offset.y + pz * offset.z);
  const qc = px * px + py * py + pz * pz - reach * reach;
  if (qc > 0) return 0;
  if (qa < 1e-12) return 1;
  return Math.min(1, (-qb + Math.sqrt(Math.max(qb * qb - 4 * qa * qc, 0))) / (2 * qa));
}

/**
 * Two-bone IK: turn `upper` and `lower` so `end` reaches `target`.
 * The elbow stays in its current bending plane and the end bone keeps its world rotation.
 */
export function reachTo(upper, lower, end, target) {
  end.getWorldQuaternion(handWorld);
  upper.getWorldPosition(a);
  lower.getWorldPosition(b);
  end.getWorldPosition(c);
  const upperLength = a.distanceTo(b);
  const lowerLength = b.distanceTo(c);
  at.subVectors(target, a);
  const distance = THREE.MathUtils.clamp(at.length(), Math.abs(upperLength - lowerLength) + 1e-4, upperLength + lowerLength - 1e-4);

  ab.subVectors(b, a).normalize();
  bc.subVectors(c, b).normalize();
  axis.crossVectors(ab, bc);
  if (axis.lengthSq() < 1e-8) axis.crossVectors(ab, Math.abs(ab.y) < 0.9 ? THREE.Object3D.DEFAULT_UP : new THREE.Vector3(1, 0, 0));
  axis.normalize();

  // Open or close the elbow until shoulder-to-wrist is the wanted distance.
  const cosNow = THREE.MathUtils.clamp(ab.dot(bc), -1, 1);
  const cosWanted = THREE.MathUtils.clamp((distance * distance - upperLength * upperLength - lowerLength * lowerLength) / (2 * upperLength * lowerLength), -1, 1);
  rotateWorld(lower, delta.setFromAxisAngle(axis, Math.acos(cosWanted) - Math.acos(cosNow)));

  // Then swing the whole arm so the wrist points at the target.
  end.getWorldPosition(c);
  ac.subVectors(c, a).normalize();
  rotateWorld(upper, delta.setFromUnitVectors(ac, at.normalize()));

  // Keep the hand's grip on the bat.
  end.parent.getWorldQuaternion(parentWorld);
  end.quaternion.copy(parentWorld.invert().multiply(handWorld)).normalize();
  end.updateWorldMatrix(true, true);
}
