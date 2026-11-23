// Which animation clip plays a shot. Presentation only: the networks have already decided the ball.
const BACK_FOOT_VERSION = { defend: "defend_back", work: "work_back", drive: "drive_back" };
const FRONT_FOOT_VERSION = { cut: "cut_front", pull: "pull_front" };
const BACK_FOOT_CLIPS = new Set(["cut", "pull", "defend_back", "work_back", "drive_back"]);

/** The front-foot or back-foot version of a shot for this length of ball. */
export function clipFor(shot, length) {
  if (length === "short" || length === "bouncer") return BACK_FOOT_VERSION[shot] ?? shot;
  if (length === "yorker" || length === "full") return FRONT_FOOT_VERSION[shot] ?? shot;
  return shot;
}

/** The foot that stays planted during a clip: "l" is the front foot, "r" the back foot. */
export function plantedFoot(clip) {
  return BACK_FOOT_CLIPS.has(clip) ? "l" : "r";
}
