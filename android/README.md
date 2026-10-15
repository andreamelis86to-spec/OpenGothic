# Android

An ARM64 NativeActivity APK using Tempest's Android backend and generated Gradle project. The A25 side-by-side workflow applies the existing touchscreen, dialogue and menu controls during the build. Automatic game-file importing is not included. Android window destruction closes the application, including when backgrounding or locking destroys its surface.

## Build

Install JDK 17, Gradle 8.9, CMake 3.22.1 or newer, Ninja and the Android SDK with SDK 35, build-tools 35.0.0, NDK 27.0.12077973 and SDK CMake 3.22.1. Set `JAVA_HOME`, `ANDROID_HOME` and `VULKAN_SDK`. Put Gradle, Ninja and the host Vulkan SDK's `glslangValidator` on `PATH`. Vulkan headers come from the host SDK; Android links the NDK's Vulkan loader.

Clone with `git clone --recursive https://github.com/Try/OpenGothic.git`, or run `git submodule update --init --recursive` in an existing checkout. Replace `/path/to/ndk` below with the NDK installation directory. The same commands work in PowerShell and a Linux shell.

```sh
cmake -S . -B build/android -G Ninja -DCMAKE_TOOLCHAIN_FILE=/path/to/ndk/build/cmake/android.toolchain.cmake -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 -DCMAKE_BUILD_TYPE=Release
cmake --build build/android --target OpenGothic-apk
```

APK: `build/android/OpenGothic-apk/build/outputs/apk/release/OpenGothic-apk-release.apk`. Use `-DCMAKE_BUILD_TYPE=Debug` for a debuggable APK under `outputs/apk/debug/OpenGothic-apk-debug.apk`. Desktop builds do not invoke the APK helper or require Android tools.

## Install and game files

The application is displayed as **OpenGothic A25** and uses package ID
`org.opengothic.optimized.a25`. It can coexist with `org.opengothic.app` and
`org.opengothic.optimized.v6`; installation does not replace those packages.
The first installation starts with separate saves and settings. Copy game files
from a PC into the new folder below; do not move or delete files belonging to an
existing installation. Do not uninstall either previous app.

The recommended APK is the `OpenGothic-A25-side-by-side-APK` artifact from the
`OpenGothic A25 side-by-side (full quality)` GitHub Actions workflow. Extract the
ZIP and install the `.apk` inside. The first A25 installation needs no `-r` flag.


Use a legally owned Gothic II: Night of the Raven installation. No game files are included in the APK. Copy the installation root, not only its `Data` directory: `Data`, `_work` and `System` must be directly inside `Gothic2`.

```sh
adb install build/android/OpenGothic-apk/build/outputs/apk/release/OpenGothic-apk-release.apk
adb shell mkdir -p /sdcard/Android/data/org.opengothic.optimized.a25/files/gothic2
adb push "/path/to/Gothic II/." /sdcard/Android/data/org.opengothic.optimized.a25/files/gothic2/
adb shell am start -n org.opengothic.optimized.a25/android.app.NativeActivity
adb logcat -s app AndroidRuntime DEBUG
```

Game files use app-specific external storage, without storage permissions. Logs, saves and writable settings use the app's internal files directory. Uninstalling removes both directories. Ray tracing and mesh shading are disabled for this initial Android build.

With a debug APK, read the file log using `adb shell run-as org.opengothic.optimized.a25 cat files/log.txt`.

## Native symbols and validation

The workflow checks the APK package ID, displayed label, arm64 ABI and signature.
It uploads `OpenGothic-A25-side-by-side-native-symbols` separately, containing the
unstripped `arm64-v8a/libGothic2Notr.so`, line information, certificate details,
APK/library SHA-256 values and the exact OpenGothic/Tempest commits. The library
comes from Gradle's `.cxx/Release` build tree. CMake passes debug line/frame-pointer
flags into the nested Gradle native build; all graphics settings remain unchanged.

Game data resolves through Android's app-specific external-data path. The current
working directory, saves, `Gothic.ini` and logs resolve through Android's internal
data path. No old package path is hardcoded or automatically migrated. Device
touch input and long-session stability still need testing on a physical phone.

Release builds currently use a runner-local debug signing key when no persistent
signing key is configured. This permits the first side-by-side installation but
does not guarantee future A25 APKs can update it. A stable private signing key must
be securely configured for future compatible updates; no key is embedded in this
repository or copied from an installed APK.
