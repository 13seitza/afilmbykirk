#!/usr/bin/env python3
import time

from evdev import InputDevice, UInput, ecodes, list_devices


REMOTE_NAME = "XING WEI 2.4G USB USB Composite Device Mouse"
ARROW_KEYS = {
    (ecodes.REL_X, -1): ecodes.KEY_LEFT,
    (ecodes.REL_X, 1): ecodes.KEY_RIGHT,
    (ecodes.REL_Y, -1): ecodes.KEY_UP,
    (ecodes.REL_Y, 1): ecodes.KEY_DOWN,
}


def find_remote():
    for path in list_devices():
        device = InputDevice(path)
        if device.name == REMOTE_NAME:
            return device
        device.close()
    return None


def tap(output, key):
    output.write(ecodes.EV_KEY, key, 1)
    output.write(ecodes.EV_KEY, key, 0)
    output.syn()


def map_remote(device, output):
    device.grab()
    last_direction = 0.0
    try:
        for event in device.read_loop():
            now = time.monotonic()
            if event.type == ecodes.EV_REL and event.value:
                direction = -1 if event.value < 0 else 1
                key = ARROW_KEYS.get((event.code, direction))
                if key and now - last_direction >= 0.18:
                    tap(output, key)
                    last_direction = now
            elif (
                event.type == ecodes.EV_KEY
                and event.code == ecodes.BTN_LEFT
                and event.value == 1
            ):
                tap(output, ecodes.KEY_ENTER)
    finally:
        try:
            device.ungrab()
        except OSError:
            pass
        device.close()


def main():
    capabilities = {
        ecodes.EV_KEY: [
            ecodes.KEY_UP,
            ecodes.KEY_DOWN,
            ecodes.KEY_LEFT,
            ecodes.KEY_RIGHT,
            ecodes.KEY_ENTER,
        ]
    }
    with UInput(capabilities, name="A Film by Kirk Remote") as output:
        while True:
            device = find_remote()
            if device is None:
                time.sleep(2)
                continue
            try:
                map_remote(device, output)
            except OSError:
                time.sleep(1)


if __name__ == "__main__":
    main()
