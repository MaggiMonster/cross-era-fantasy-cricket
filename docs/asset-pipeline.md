# Asset pipeline: motion capture and faces

Researched in Turn 4 (2026-11-23). **Nothing here has been installed or run yet**, so
quality notes come from published results and project documentation, not our own tests.
The chosen methods are recorded under "Decisions".

## Where assets live

Player photos, generated heads and source clips are never committed.

```text
~/cricket-project/assets/
  SOURCES.md     where every photo and clip came from, with its licence
  photos/<player>/
  clips/<shot or action>/
  characters/<player>.glb
  raw/<source>/<action>/<take>.fbx
  animations/<source>/<action>.glb
```

`npm run dev` serves `.glb`, `.gltf` and image files from that folder at
`/player-assets/...`, on this Mac only (`web/vite.config.js`). For example:
`/player-assets/characters/kohli.glb`. A production build does not copy them.

## The source clips are the biggest constraint

A search of Wikimedia Commons (openly licensed media) on 2026-11-23 found:

| Needed | Found |
|--------|-------|
| Bumrah bowling | **None** (no video matches his name) |
| Warne bowling | **None** (no video matches his name) |
| Tendulkar batting | **None** (one video, an award ceremony) |
| Kohli batting | One short dismissal clip, not enough for eight shots |
| Generic club cricket | Many clips (about 1,400 search hits for "cricket batting", 340 for "cricket bowling", some unrelated) |

The search was rate-limited before we could count clips for each individual shot or
for leg-spin, so those are **unknown**. Open photos exist for Tendulkar (206 search
hits), Kohli (135) and Bumrah (12). The Warne count was not obtained.

Consequence: under the no-YouTube, no-broadcast rule, the animations cannot be
captured from the four real players. Realistic options are club clips from Commons, or
filming ourselves or a friend copying each player's action. Self-filming gives the best
capture conditions: fixed camera, full body in frame, high frame rate, one person.

## Motion capture options

| Option | Quality | Cost | Runs on | Account or upload |
|--------|---------|------|---------|-------------------|
| **ExMR** (2026) | Newest here. World-grounded body, **hands and feet**, foot contact handling. BVH and Blender export | Free, education and research licence | NVIDIA, about 8 GB, tested on Linux | SMPL-X registration and gated SAM 3D Body access. No video upload |
| **GVHMR** (2024) | Strong, well used. Body only. Beat WHAM on its own benchmarks | Free, education and non-profit licence | NVIDIA. A small community fork claims Apple Silicon support (unverified) | SMPL/SMPL-X registration. No video upload |
| WHAM (2024) | Good, older, accumulates drift | Free, MIT code | NVIDIA | SMPL registration |
| TRAM (2024) | Strong camera handling, helps moving cameras | Free, MIT code | NVIDIA | SMPL registration |
| 4D-Humans (2023) | Good per-frame pose, no world trajectory | Free, MIT code | NVIDIA preferred | SMPL registration |
| Rokoko Vision | Easy, FBX output | Free 30 s/month, then from $10-12/month | Website | **Account and cloud upload**. Its terms give Rokoko a perpetual licence to process content |
| DeepMotion | Easy, FBX/BVH/GLB | Free 60 s/month, non-commercial | Website | **Account and cloud upload** |
| Move.ai | Could not be checked (pricing page unavailable) | Unknown | Website/app | Account and upload |
| Mixamo library | Clean animation, but we could not confirm any cricket motions | Free | Website | **Adobe account**. Page could not be read |
| MediaPipe (`archive/pose`) | **Fallback only.** 33 joints, no body mesh or joint rotations | Free | This Mac | None |

**Research recommendation: ExMR on the RTX 4060, with GVHMR as the backup.** We are
starting with DeepMotion for speed and will compare ExMR later (see "Decisions"). Batting and bowling
depend on foot placement and hands on the bat, which ExMR models and GVHMR does not. Both
run locally, so no footage leaves our machines. The risk is that 8 GB is exactly ExMR's
tested memory size, and it was tested on Linux. Test one clip before relying on it.
Output is retargeted to the character rig with Blender scripts.

Licence: SMPL-X, ExMR and GVHMR allow non-commercial education use. The SMPL-X model
files must not be redistributed, so they also stay out of git. This suits a private
university project, but **the game could not be sold under these licences**.

### What the earlier pose work taught us

`archive/pose` ran MediaPipe on a real clip. The skeleton jumped between people, broke at
camera cuts, and the batter was only about 120 pixels tall. Smoothing cut jitter from 6.0
to 1.4 pixels but risks rounding off the bat swing. So we now want: a person tracker,
single-shot clips with the player large in frame, world-space motion, joint rotations
that drive a rig, and speed-aware smoothing.

## Face options

| Option | Realism | Cost | Runs on | Output and catches |
|--------|---------|------|---------|--------------------|
| **KeenTools FaceBuilder** (Blender) | High for likeness when given several photos, with manual alignment | 15-day free trial, then $19.99/month | **This Mac** (Apple Silicon) | Normal textured mesh, easy to export to glTF. Trial sign-up steps not confirmed |
| MICA / DECA / EMOCA / SMIRK (FLAME) | Accurate shape, weaker skin and hair | Free, non-commercial | Mostly NVIDIA; Mac untested | FLAME registration. Face only, so hair and neck need manual work |
| GAGAvatar / LAM | Most photoreal in motion | Free (MIT / Apache) | NVIDIA | Gaussian splats, not a mesh. Hard to attach to a rigged glTF body |
| TRELLIS | Whole-object generation, likeness not reliable | Free, MIT | NVIDIA **16 GB**, more than the RTX 4060 | Mesh output |
| Hunyuan3D-2 | Good general 3D, likeness not reliable | Free, restricted licence | NVIDIA | Licence excludes EU, UK, South Korea and bars impersonation without consent |

**Recommendation: FaceBuilder on its free trial**, using 3 to 6 openly licensed photos per
player. It is the only option that runs on this Mac and directly produces the textured
mesh a rigged glTF character needs. All four heads must be finished inside the 15 days
or it needs a paid month. The free fallback is MICA plus a hand-projected photo texture,
which will look noticeably less realistic.

## Decisions

- **Motion capture (decided 2026-11-23): start with an online service, DeepMotion
  Animate 3D**, to get working animations quickly. Apurva creates the account and uploads
  the clips personally. Later, run the same clips through ExMR on Apurva's RTX 4060
  (Windows, via WSL) and compare side by side.
- **Why DeepMotion over Rokoko:** its free tier is 60 s a month against Rokoko's 30 s. All
  ten actions need about 37 s, leaving room for reruns.
- **Face method and clip source: still open.** See `HANDOFF.md`.

## Source-independent motion pipeline

The game must never know which tool made an animation. Every source goes through the
same steps and produces the same files:

```text
clips/<action>/<take>.mp4              one trimmed master clip, used by every source
raw/<source>/<action>/<take>.fbx       untouched tool output (source: deepmotion, exmr)
animations/<source>/<action>.glb       retargeted to our one character rig
```

- `<action>` is one of `leave`, `defend`, `work`, `drive`, `cut`, `pull`, `sweep`, `loft`,
  `bumrah_delivery`, `warne_delivery`.
- Each `.glb` has one clip named after the action, the same rig, 30 fps, and root motion
  handled the same way. Only the retargeting input differs per source.
- Turn 5 should let the game pick a source with `?motion=deepmotion` or `?motion=exmr`.
- **Comparison:** same master clip, same rig and camera, played side by side. Score foot
  sliding, bat and hand position, fast-swing accuracy and jitter.
- ExMR under WSL is **untested**. Its authors tested native Linux with about 8 GB of GPU
  memory, which is all an RTX 4060 has. Test one clip first.

## DeepMotion: what to click

Labels marked *(check)* could not be confirmed from DeepMotion's docs and may differ.

Before uploading: trim each clip to only the action (about 3 s per shot, 5 to 8 s per
bowling action), one person, full body, fixed camera, MP4 or MOV, under 50 MB.

1. Go to <https://www.deepmotion.com/animate-3d> and click **Free to Use - Sign Up Now**.
2. Choose **Create Freemium Account**. No card is needed. Do not click **Upgrade**.
3. Open the activation email, click **Please Click Here to Activate Your Account**, and
   set a password.
4. Sign in at <https://portal.deepmotion.com> with your email as the username.
5. Click **Animate 3D**, then **Create**.
6. Upload one clip and label it with the action name, for example `drive`.
7. Keep **Foot Locking** on **Auto** and turn **Physics Simulation** on *(check)*. Leave
   **Face & Hand Tracking off**, because it costs 1.5 credits per second instead of 1.
   Leave **Speed Multiplier** at its default unless the clip is slow motion.
8. Confirm the credit cost, then start the job *(check)*.
9. Check the preview. Rerun only if needed, because reruns may use credits.
10. Download **FBX** *(check)* and save it as
    `~/cricket-project/assets/raw/deepmotion/<action>/<take>.fbx`.
11. Add the clip's origin to `~/cricket-project/assets/SOURCES.md`.

Privacy: DeepMotion's terms let it process uploads through machine-learning models to
improve its services. Upload only clips you are allowed to share, and get consent from
anyone recognisable. Free-tier output is for non-commercial use only.

## Sources

- [GVHMR](https://github.com/zju3dv/GVHMR), [Apple Silicon fork](https://github.com/ryanrudes/gvhmr), [ExMR](https://github.com/twehrbein/ExMR), [WHAM](https://github.com/yohanshin/WHAM), [TRAM](https://github.com/yufu-wang/tram), [4D-Humans](https://github.com/shubham-goel/4D-Humans), [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body)
- [SMPL-X licence](https://smpl-x.is.tue.mpg.de/modellicense.html), [FLAME licence](https://flame.is.tue.mpg.de/modellicense.html)
- [Rokoko pricing](https://www.rokoko.com/pricing), [Rokoko terms](https://www.rokoko.com/terms-of-use-update), [DeepMotion Animate 3D](https://www.deepmotion.com/pricing-animate3d)
- [FaceBuilder](https://keentools.io/products/facebuilder-for-blender), [FLAME-Universe](https://github.com/TimoBolkart/FLAME-Universe), [GAGAvatar](https://github.com/xg-chu/GAGAvatar), [LAM](https://github.com/aigc3d/LAM), [TRELLIS](https://github.com/microsoft/TRELLIS), [Hunyuan3D-2 licence](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE)
- [Wikimedia Commons](https://commons.wikimedia.org)
