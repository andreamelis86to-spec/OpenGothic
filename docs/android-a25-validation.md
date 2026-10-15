# Android Galaxy A25: changes and validation

Base: `opengothic-v6-test`, commit `5696a8f49ccb5e5df705705ac0a0f6e4b2576b11`.
Working branch: `opengothic-v6-a25-stability`.

## Findings and changes

- `VisualObjects::free` previously erased wind membership only when wind was
  NONE. A freed WIND/WIND_ALT id survived, and `preFrameUpdateWind` subsequently
  indexed a reset or removed object. Erase membership unconditionally before
  shrinking the vector. This also avoids redundant per-frame work for stale ids.
- Animated texture names used a 128-byte stack buffer with a late `>` check.
  Boundary-length names could overwrite memory or lose termination. Build names
  and the `.TGA` fallback with `std::string`, preserving case conversion and frame
  lookup order. The existing `string_frm` fallback also overflowed for long names;
  this path now avoids it. This does not repair every other use of that helper.
- The worker pool always created 16 threads. Allocate only
  `min(max(hardware_concurrency, 1), 16)` threads, and wake exactly that many on
  shutdown. An Android system reporting eight CPUs now creates eight workers.
  This reduces idle thread stacks and unnecessary wakeups. Performance and
  thermal improvements require measurement on the phone.
- Explicit task ids no longer use pointer arithmetic on nullptr.
- Remove the unused `ddsBuf` and its 8 MiB reservation; let the sound scratch
  buffer `fBuff` grow when needed instead of reserving another 8 MiB at startup.
  This removes requested capacity, not a measured 16 MiB reduction in resident
  memory. Loaded textures/meshes retain their existing ownership and lifetime.

No texture resolution, mipmaps, effects, draw distance or material settings are
reduced. Package name remains `org.opengothic.optimized.v6`. No application
manifest, save-path code, or original workflow is changed.

## New APK workflow

`.github/workflows/opengothic-a25-stability.yml` derives from the V6 workflow and:

- runs on push to the new branch or manual dispatch;
- preserves and verifies the existing touch/dialogue/menu patches;
- pins Tempest to `3e401418ad61f219871699b0418a15fc6ce1c7af` rather than moving master;
- omits touch diagnostic logging injections;
- retains the source's 2048 shadow resolution (the old V6 workflow reduced it to 1024);
- builds arm64 Release with line information and frame pointers;
- uploads the APK and unstripped native game library separately for symbolication;
- times out after 60 minutes and runs the host regression suite before building.

The 2048 shadows cost more GPU memory/work than the old 1024 build. This is
intentional to respect full source quality; FPS improvements over that APK cannot
be assumed. Existing APK signing/update compatibility has not been verified.
Keep the installed app and saves until signing compatibility is confirmed.

## Checks performed

`ASAN_OPTIONS=detect_leaks=0 python3 tests/a25_regressions.py` passes:

- production texture-name method at boundary sizes 120 through 129 and up to
  4096 characters, including fallback lookup;
- production object-free method over 1000 lifecycle repetitions for each wind
  mode, including interior-id reuse and vector shrinking;
- production worker implementation with emulated CPU reports 0, 1, 2, 8 and 16:
  repeated parallel loops, exact-once task indices, empty/single-task batches,
  boundary batch sizes and shutdown.

These are host C++ checks with AddressSanitizer and UndefinedBehaviorSanitizer.
GPU, assets and scene services are stubbed for the two extracted methods. Worker
tests compile the implementation with unused Tempest includes removed and CPU
count queries replaced by the test value. LeakSanitizer cannot operate under
this environment's tracing restrictions and was disabled; ASan/UBSan remain on.

Workflow YAML and embedded Python syntax validated. All three touch/dialogue/menu
patch steps executed successfully against the exact base files in an isolated
temporary repository. `git diff --check` passed.

The same regression suite run against the original methods failed with a
reproducible AddressSanitizer heap-buffer-overflow in the texture fallback.

Full game compilation, Android APK generation, phone FPS, resident memory and
long-session stability have **not** been verified. Remote branch creation failed
with GitHub API 403 `Resource not accessible by integration`; no workflow was
started and no APK was produced in this session. The local checkout contains
the complete base tree but only inspected source blobs, so it is not a full
offline build checkout. The exported patch can be applied to a normal clone.

## Required device comparison

Use the same Gothic 2 assets, save, route, resolution, settings, temperature and
charging state for at least three runs per APK. Explore for 30–60 minutes,
including vegetation, city/countryside transitions, combat, dialogue and a
save/load cycle. Compare median/p95/p99 frame times and periodic PSS, native heap
and graphics memory. Distinguish thermal throttling from increasing memory use.

Record `adb logcat -v threadtime` and periodically
`adb shell dumpsys meminfo org.opengothic.optimized.v6`. Preserve crash logs,
build SHA, Tempest SHA and the matching native-symbol artifact. Android native
tombstones, Java exceptions, low-memory process kills and GPU failures require
different fixes. A native signal backtrace should be symbolicated with that
build's unstripped library. No claim that the reported phone crashes are fixed
is supported until this comparison is performed.
