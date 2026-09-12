import json
import re
import shutil
import subprocess


class ControlError(RuntimeError):
    pass


def _run(command, timeout=30):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        ).stdout.strip()
    except FileNotFoundError as error:
        raise ControlError(f"{command[0]} is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise ControlError(f"{command[0]} timed out") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip() or "command failed"
        raise ControlError(message) from error


def _split_nmcli(line):
    fields = []
    current = []
    escaped = False
    for character in line:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    fields.append("".join(current))
    return fields


def wifi_status():
    if not shutil.which("nmcli"):
        return {"available": False, "connected": "", "networks": []}
    connected = _run(["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"])
    active = ""
    for line in connected.splitlines():
        fields = _split_nmcli(line)
        if len(fields) >= 2 and fields[0] == "yes":
            active = fields[1]
            break
    return {"available": True, "connected": active}


def scan_wifi():
    output = _run(
        [
            "nmcli",
            "-t",
            "-f",
            "IN-USE,SSID,SIGNAL,SECURITY",
            "device",
            "wifi",
            "list",
            "--rescan",
            "yes",
        ],
        timeout=45,
    )
    networks = {}
    for line in output.splitlines():
        fields = _split_nmcli(line)
        if len(fields) < 4 or not fields[1]:
            continue
        in_use, ssid, signal, security = fields[:4]
        candidate = {
            "ssid": ssid,
            "signal": int(signal or 0),
            "security": security or "Open",
            "connected": in_use == "*",
        }
        if ssid not in networks or candidate["signal"] > networks[ssid]["signal"]:
            networks[ssid] = candidate
    return sorted(
        networks.values(), key=lambda item: (not item["connected"], -item["signal"])
    )


def connect_wifi(ssid, password=""):
    ssid = str(ssid).strip()
    if not ssid or len(ssid) > 32 or any(ord(char) < 32 for char in ssid):
        raise ControlError("Choose a valid Wi-Fi network")
    command = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        command.extend(["password", str(password)])
    _run(command, timeout=60)
    return wifi_status()


def volume_status():
    if shutil.which("wpctl"):
        output = _run(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]
        )
        match = re.search(r"Volume:\s+([0-9.]+)", output)
        if match:
            return {
                "available": True,
                "percent": round(float(match.group(1)) * 100),
                "muted": "[MUTED]" in output,
            }
    return {"available": False, "percent": 0, "muted": False}


def change_volume(action):
    if not shutil.which("wpctl"):
        raise ControlError("System volume is unavailable")
    commands = {
        "up": ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+"],
        "down": ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"],
        "mute": ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
    }
    if action not in commands:
        raise ControlError("Unknown volume action")
    _run(commands[action])
    return volume_status()


def audio_outputs():
    if not shutil.which("pactl"):
        return []
    try:
        default_name = _run(["pactl", "get-default-sink"])
        sinks = json.loads(_run(["pactl", "-f", "json", "list", "sinks"]))
    except (ControlError, json.JSONDecodeError):
        return []
    outputs = []
    for sink in sinks:
        name = sink.get("name", "")
        if not name:
            continue
        properties = sink.get("properties", {})
        outputs.append(
            {
                "id": name,
                "name": properties.get("device.description")
                or sink.get("description")
                or name,
                "bluetooth": "bluez" in name,
                "selected": name == default_name,
            }
        )
    return outputs


def select_audio_output(output_id):
    output = next(
        (item for item in audio_outputs() if item["id"] == output_id), None
    )
    if output is None:
        raise ControlError("Audio output is no longer available")
    _run(["pactl", "set-default-sink", output_id])
    return audio_outputs()


BLUETOOTH_ADDRESS = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def scan_bluetooth():
    if not shutil.which("bluetoothctl"):
        raise ControlError("Bluetooth tools are not installed")
    try:
        _run(["bluetoothctl", "--timeout", "8", "scan", "on"], timeout=12)
    except ControlError:
        # Discovery may time out after still populating the device list.
        pass
    output = _run(["bluetoothctl", "devices"])
    devices = []
    for line in output.splitlines():
        match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)", line)
        if match:
            devices.append({"address": match.group(1).upper(), "name": match.group(2)})
    return devices


def connect_bluetooth(address):
    address = str(address).upper()
    if not BLUETOOTH_ADDRESS.fullmatch(address):
        raise ControlError("Invalid Bluetooth device")
    # Most speakers use no-input/no-output pairing. Trusting enables reconnects.
    try:
        _run(
            ["bluetoothctl", "--agent", "NoInputNoOutput", "pair", address],
            timeout=35,
        )
    except ControlError:
        # A previously paired device can still be trusted and connected.
        pass
    _run(["bluetoothctl", "trust", address])
    _run(["bluetoothctl", "connect", address], timeout=30)
    return {"connected": True, "address": address}
