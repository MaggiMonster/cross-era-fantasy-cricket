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

Current decisions (2026-11-23, Turn 5):

- **Faces: KeenTools FaceBuilder**, on its 15-day trial.
- **No self-filming and no copyrighted match footage.**
- **Motion: ready-made cricket packs if one is approved, otherwise scripted Blender
  keyframes.** Mixamo may supply generic running. Nothing is bought without asking.
- **DeepMotion and ExMR are no longer the main plan.** Their notes below are kept for
  reference only.

## FaceBuilder photo checklist

Collect **6 to 8 photos per player before starting the trial**. KeenTools recommends 4 to
8 from different angles. The rest of this list is our practical guidance.

| # | Angle | Why |
|---|-------|-----|
| 1 | Front, looking at the camera | Face width, eyes, mouth |
| 2 | Three-quarter left (about 45 degrees) | Most useful single view for 3D shape |
| 3 | Three-quarter right (about 45 degrees) | Same, other side |
| 4 | Left profile, or as near as available | Nose, jaw and forehead depth |
| 5 | Right profile, or as near as available | Same, other side |
| 6 | Slightly from below | Jaw and chin |
| 7 | Slightly from above | Forehead and hairline |
| 8 | Extra clear front or three-quarter | Best source for the skin texture |

- **Same period:** all photos from within a few years, with the same hair and beard.
  Suggested: Sachin about 2008-2013, Kohli 2018 onwards, Bumrah 2019 onwards, Warne about
  2005-2010.
- **Clear face:** no helmet, cap, sunglasses, hands, microphone or heavy shadow.
- **Quality:** sharp eyes, soft even light, and the head at least 500 pixels tall (1000 or
  more is better). Avoid heavy compression, filters and wide-angle close-ups.
- **Expression:** neutral or a closed-mouth smile.
- **Licence:** prefer Wikimedia Commons. Record each file in
  `~/cricket-project/assets/SOURCES.md` and save it to `photos/<player>/`.

**Trial terms.** KeenTools states the trial is 15 days from first launch "with no
restrictions or limitations", that you can "export your unique model outside Blender in any
3D supporting format", and that after it ends you can still open projects and export but
not edit. The page does not name glTF, and we have **not yet tested a textured export** or
confirmed support for Blender 5.3. Export one test head to `.glb` on day one. The clock
covers all four heads, so both contributors should have photos ready first.

## Animation pack options

Checked 2026-11-23. **Nothing has been bought.** CGTrader listing pages and TurboSquid could
not be opened by our tools, so items marked *search only* come from search-result text and
must be checked on the page.

| Option | Price | Licence | Actions covered (of 10) |
|--------|-------|---------|-------------------------|
| **CGTrader "Cricket Animations"** (best lead) | Not confirmed | CGTrader royalty-free, *not confirmed for this item* | *Search only:* batting strokes plus fast and spin bowling. Exact shots unknown |
| Unity Asset Store "Cricket Bowling Animations Pack" (HK) | Free | Standard Unity EULA, not yet read for non-Unity use | 8 bowling clips. Fast or leg-spin not stated, 0 batting |
| TurboSquid batter and bowler pack | $159, *search only* | Not confirmed | Not confirmed |
| CGTrader animated hook-shot batsman | $28, *search only* | Not confirmed | Pull or hook only, at most |
| Animium "Cricket Batting" | $1.50 plus Bronze membership | Not stated | 1 clip, partial defend |
| ActorCore, Fab, Sketchfab | n/a | n/a | No cricket pack found |
| Mixamo | Free, Adobe account | Royalty-free for games per Adobe's FAQ (search text). Raw files may not be redistributed | Generic running only |

**Licence risk.** CGTrader's terms restrict products that can be extracted from an
application. A browser game serves its `.glb` files to the browser, so a purchased pack is
fine on our own machines but **should not be deployed publicly** without checking the
licence. Our dev server already keeps these files local.

## Motion pipeline

The game must never know which tool made an animation:

```text
pipeline/build_batter.py               builds the rigged batters and scripted clips
raw/<source>/<action>/<take>.fbx       untouched pack or tool output
animations/<source>/<player>.glb       one clip per action on our rig
characters/<player>.glb                body, kit, bat and rig
```

- Install the free MPFB extension once: `blender --online-mode --command extension install --sync --enable mpfb`.
- Rebuild: `blender --background --python pipeline/build_batter.py -- tendulkar kohli`. Do not
  add `--factory-startup`, because it disables MPFB.
- Bodies use MPFB 2.0.18 and its `game_engine` rig, with fingers. MPFB's code is GPL. A 2025
  CGChannel article says content made with it is CC0, which we did not confirm on MPFB's own pages.
- `<action>` is one of `idle`, `leave`, `defend`, `work`, `drive`, `cut`, `pull`, `sweep`,
  `loft`, `bumrah_delivery`, `warne_delivery`.
- Swing clips are 30 fps and 1.0 s long, with bat contact at 0.4 s.
- Pick a source with `?motion=scripted` (default). Review a pose with `?pose=drive:0.4`, or
  play from beside the batter with `?closeup=1`.
- The `Head` mesh is separate from `Body`, so a FaceBuilder head can replace it.

## Signature touches

Stylised from general knowledge of each player, not measured.

- **Sachin (built):** compact, narrow base, low crouch, short controlled backlift.
- **Kohli (built):** upright, wider base, high backlift, fuller follow-through.
- **Bumrah (spec for Turn 6):** short, stuttering, jerky run-up, very front-on chest at
  delivery, near-straight bowling arm, late whip of the wrist.
- **Warne (spec for Turn 6):** unhurried walk-in of a few paces, side-on load, strong
  shoulder rotation, and a big wrist and finger flick for leg-spin.

## Reference only: earlier DeepMotion plan

No longer the main plan. Keep only in case the decision changes.

### DeepMotion: what to click

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
