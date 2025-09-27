#!/usr/bin/env python3
"""
envvenv.py – Apply deterministic world‑state settings to mobile simulators or emulators.

EnvVenv reads a YAML configuration describing the target platform, device name,
and desired world state (timezone, locale, network profile, GPS coordinates,
battery level, and application launch arguments).  It then uses `adb` for
Android or `xcrun simctl` for iOS to apply those settings and launch the app.

This script is intended for development and QA hand‑offs.  It does not
repackage or modify applications, nor does it attempt to circumvent
platform protections.  You should only run it against devices and apps
for which you have permission to automate.

Example:
    python3 envvenv.py --config my_repro.yaml
"""

import argparse
import os
import subprocess
import sys
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except ImportError as exc:
    raise SystemExit(
        "PyYAML is required to parse configuration files.  Install it with\n"
        "    pip install pyyaml\n"
        "and re‑run this script."
    ) from exc


def run(cmd: list[str]) -> None:
    """Run a command, printing it first for clarity."""
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def apply_android(cfg: Dict[str, Any]) -> None:
    """Apply world state and launch the app on an Android emulator/device."""
    world: Dict[str, Any] = cfg.get("world", {})
    app: Dict[str, Any] = cfg.get("app", {})

    # Disable automatic time and timezone and set them explicitly.
    if "timezone" in world:
        tz = world["timezone"]
        run(["adb", "shell", "settings", "put", "global", "auto_time", "0"])
        run(["adb", "shell", "settings", "put", "global", "auto_time_zone", "0"])
        run(["adb", "shell", "setprop", "persist.sys.timezone", tz])

    # Locale
    if "locale" in world:
        locale = world["locale"]
        run(["adb", "shell", "setprop", "persist.sys.locale", locale])
        # Restart may be required; stop/start services to apply locale.
        run(["adb", "shell", "stop"])
        run(["adb", "shell", "start"])

    # Network profile and latency via emulator console commands.
    network: Optional[Dict[str, Any]] = world.get("network")
    if network:
        profile = network.get("profile")
        latency = network.get("latency")
        if profile:
            run(["adb", "emu", "network", "speed", profile])
        if latency:
            run(["adb", "emu", "network", "delay", latency])

    # GPS coordinates
    gps: Optional[Dict[str, Any]] = world.get("gps")
    if gps:
        lat = gps.get("lat")
        lon = gps.get("lon")
        if lat is not None and lon is not None:
            run(["adb", "emu", "geo", "fix", str(lon), str(lat)])

    # Battery level
    if "battery" in world:
        level = world["battery"]
        run(["adb", "shell", "dumpsys", "battery", "set", "level", str(level)])

    # Install and launch the app.
    package_name = app.get("package")
    apk_path = app.get("apk")
    launch_args: Dict[str, Any] = app.get("launch_args", {})
    activity_override = app.get("activity")
    if package_name:
        if apk_path:
            # Install the APK if provided.
            run(["adb", "install", "-r", apk_path])
        # Clear app data to ensure a clean state.
        run(["adb", "shell", "pm", "clear", package_name])
        # Build the am start command with extras.
        if activity_override:
            if "/" in activity_override:
                component = activity_override
            elif activity_override.startswith("."):
                component = f"{package_name}/{activity_override}"
            elif "." in activity_override:
                component = f"{package_name}/{activity_override}"
            else:
                component = f"{package_name}/.{activity_override}"
        else:
            component = f"{package_name}/.MainActivity"

        cmd = ["adb", "shell", "am", "start", "-n", component]
        for key, value in launch_args.items():
            if isinstance(value, bool):
                cmd.extend(["--ez", key, "true" if value else "false"])
            elif isinstance(value, int):
                cmd.extend(["--ei", key, str(value)])
            elif isinstance(value, float):
                cmd.extend(["--ef", key, str(value)])
            elif isinstance(value, (list, tuple)):
                cmd.extend(["--esa", key, ",".join(map(str, value))])
            else:
                cmd.extend(["--es", key, str(value)])
        run(cmd)
    else:
        print("No package specified; skipping app installation and launch.")


def apply_ios(cfg: Dict[str, Any]) -> None:
    """Apply world state and launch the app on an iOS simulator."""
    world: Dict[str, Any] = cfg.get("world", {})
    app: Dict[str, Any] = cfg.get("app", {})
    device_udid = cfg.get("device")
    if not device_udid:
        raise ValueError("For iOS targets you must specify the simulator UDID in the 'device' field.")

    # Boot the simulator if not already running.
    run(["xcrun", "simctl", "boot", device_udid])

    # Timezone and locale – best set via dependency injection; host timezone also influences simulators.
    if "timezone" in world:
        tz = world["timezone"]
        # iOS simulators read the host timezone; you can set the host timezone temporarily.
        print(f"Info: Set host timezone to {tz} before running the simulator.")

    # Network conditions (requires Xcode 15+).
    network: Optional[Dict[str, Any]] = world.get("network")
    if network:
        profile = network.get("profile")
        if profile:
            # Example: '3g', '4g', 'wifi' etc.  Note that simctl supports limited presets.
            run(["xcrun", "simctl", "io", device_udid, "speed", profile])

    # GPS coordinates
    gps: Optional[Dict[str, Any]] = world.get("gps")
    if gps:
        lat = gps.get("lat")
        lon = gps.get("lon")
        if lat is not None and lon is not None:
            run(["xcrun", "simctl", "location", device_udid, "set", f"{lat},{lon}"])

    # Battery level and state
    if "battery" in world:
        level = world["battery"]
        # batteryState options: 'charged', 'discharging', 'charging', 'unplugged'
        run(["xcrun", "simctl", "status_bar", device_udid, "override", "--batteryState", "charged", "--batteryLevel", str(level)])

    # Install and launch the app.
    bundle_id = app.get("package")
    app_path = app.get("app_path")
    launch_args: Dict[str, Any] = app.get("launch_args", {})
    launch_env: Dict[str, Any] = app.get("launch_env", {})
    if bundle_id:
        if app_path and os.path.exists(app_path):
            run(["xcrun", "simctl", "install", device_udid, app_path])
        # Uninstall first to ensure a clean start.
        run(["xcrun", "simctl", "uninstall", device_udid, bundle_id])
        if app_path and os.path.exists(app_path):
            run(["xcrun", "simctl", "install", device_udid, app_path])
        # Construct launch command with environment variables.
        cmd = ["xcrun", "simctl", "launch", device_udid]
        for key, value in launch_env.items():
            cmd.extend(["--env", str(key), str(value)])
        cmd.append(bundle_id)
        for key, value in launch_args.items():
            cmd.extend(["--args", f"-{key}={value}"])
        run(cmd)
    else:
        print("No bundle ID specified; skipping app installation and launch.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply deterministic world state to mobile devices.")
    parser.add_argument("--config", required=True, help="Path to a YAML file describing the desired environment")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg: Dict[str, Any] = yaml.safe_load(f)

    platform = cfg.get("platform")
    if platform == "android":
        apply_android(cfg)
    elif platform == "ios":
        apply_ios(cfg)
    else:
        raise ValueError("Invalid or missing 'platform' field; must be 'android' or 'ios'.")


if __name__ == "__main__":
    main()