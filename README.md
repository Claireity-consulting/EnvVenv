# EnvVenv

**EnvVenv** is a lightweight toolkit for reproducing bugs across different hand‑held devices by making the runtime environment as deterministic as possible.  When you capture a failing run on one device, EnvVenv lets you replay the same world state—time, timezone, locale, network profile, GPS location, battery level, and more—on a clean simulator or emulator.  This helps QA and developers hand off bugs without the usual “works on my machine” friction.

> **Important:** EnvVenv is *not* a sandbox or a tool to evade platform security.  It doesn’t re‑package apps or hide their provenance.  It simply orchestrates supported tools like `adb` and `xcrun` to apply settings that your app would otherwise read from the device.  Use it only in environments where you have permission to run automated tests.

## Getting started

EnvVenv uses a simple YAML file to describe the desired world state.  You can use the provided `repro_template.yaml` as a starting point.  A minimal example:

```yaml
# Platform being targeted (android or ios).  Determines which toolchain is used.
platform: android

# Device template name.  For Android this should match a managed emulator name; for iOS this is the UDID of a simulator clone.
device: pixel6_api34

# World state section controls the environment visible to your app.
world:
  timezone: "Europe/Brussels"
  locale: "en-US"
  network:
    profile: "lte"
    latency: "gprs"
  gps:
    lat: 50.8503
    lon: 4.3517
  battery: 27

# App configuration for launch.  You can pass extra arguments or environment variables here.
app:
  package: "com.example.app"
  app_path: "/path/to/MyApp.app"  # iOS only; omit to reuse an already-installed build

  activity: "com.example.app.ui.CheckoutActivity"
  launch_args:
    TestProfile: "checkout"
    RNG_SEED: 12345
    EnableCoupons: true
    SupportedLocales:
      - "en-US"
      - "fr-FR"
  launch_env:  # iOS only
    API_ROOT: "https://staging.example.com"
```

Once you have a YAML file, run the `envvenv.py` script to apply it:

```bash
python3 envvenv.py --config my_repro.yaml
```

The script will determine whether you are targeting Android or iOS and issue the appropriate shell commands.  For Android it uses `adb` and the emulator console; for iOS it uses `xcrun simctl`.  If a section is omitted from the YAML, EnvVenv leaves that aspect untouched.

Android launch arguments are typed automatically based on their YAML representation—booleans are sent with `--ez`, integers with `--ei`, floats with `--ef`, and lists become comma‑separated string arrays.  On iOS you can now inject deterministic environment variables alongside the CLI arguments by using the `launch_env` map.

If you omit `app.app_path` for an iOS configuration, EnvVenv will skip installation and simply launch whichever build of the bundle identifier is already present on the simulator.

## Scripts

The `scripts/` directory contains ready‑made shell scripts that wrap EnvVenv for common cases:

* **run_android_repro.sh** – boots (or waits for) an Android emulator, applies deterministic world state, installs your APK, and launches it with the specified arguments.
* **run_ios_repro.sh** – similarly bootstraps an iOS simulator, applies the world state, installs the `.app` bundle, and launches it with arguments.  (Requires macOS with Xcode installed.)

Feel free to customise these scripts to your project.  They are examples rather than strict APIs.

## YAML schema overview

| Key        | Type        | Description |
|------------|------------|-------------|
| `platform` | string      | Target platform: `android` or `ios`. |
| `device`   | string      | Emulator device name (Android) or simulator UDID (iOS). |
| `world`    | map         | Environment settings.  Each subkey is optional. |
| `world.timezone` | string | IANA timezone identifier (e.g. `Europe/Brussels`). |
| `world.locale` | string | Locale string in language‑territory format (e.g. `en-US`). |
| `world.network.profile` | string | Network speed preset (Android only): `gsm`, `edge`, `umts`, `lte`, etc. |
| `world.network.latency` | string | Additional latency preset: `none`, `gprs`, `edge`, etc. |
| `world.gps.lat` / `world.gps.lon` | number | Latitude and longitude for the virtual GPS. |
| `world.battery` | integer | Battery level percentage (0–100). |
| `app.package` | string | Bundle identifier or package name of your app. |
| `app.app_path` | string | (iOS) Path to the `.app` bundle to install.  Leave unset to launch an already installed build. |
| `app.activity` | string | (Android) Component name or activity class to launch.  Defaults to `.MainActivity`. |
| `app.launch_args` | map | Key‑value pairs passed as extras (Android) or CLI arguments (iOS).  Android extras are typed automatically based on YAML values. |
| `app.launch_env` | map | (iOS) Environment variables injected when launching the app. |

## License

This project is licensed under the MIT License.  See `LICENSE` for details.
