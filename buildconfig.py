#!/usr/bin/env python3
import json
import mido
import sys


def choose_port():
    ports = mido.get_output_names()
    if not ports:
        print("No MIDI output ports available.")
        sys.exit(1)

    print("Available MIDI output ports:")
    for i, name in enumerate(ports, start=1):
        print(f"  [{i}] {name}")

    while True:
        choice = input(f"Select port [1-{len(ports)}]: ")
        try:
            idx = int(choice)
            if 1 <= idx <= len(ports):
                return ports[idx - 1]
        except ValueError:
            pass
        print("Invalid selection, try again.")


def choose_channel():
    """
    Prompt for MIDI channel (1-16) and return 0-15.
    """
    while True:
        choice = input("Enter MIDI channel (1-16) [default 1]: ") or "1"
        try:
            ch = int(choice)
            if 1 <= ch <= 16:
                return ch - 1
        except ValueError:
            pass
        print("Invalid channel, must be integer 1-16.")


def choose_files():
    """
    Prompt for comma-separated JSON song file paths.
    """
    files = input("Enter JSON song files (comma-separated): ")
    parts = [f.strip() for f in files.split(',') if f.strip()]
    if not parts:
        print("You must specify at least one file.")
        return choose_files()
    return parts


def choose_output_midi():
    default = "song.mid"
    path = input(f"Enter output MIDI file path [default {default}]: ") or default
    return path


def choose_config_path():
    default = "config.json"
    path = input(f"Enter config file path [default {default}]: ") or default
    return path


def main():
    print("MIDI Configuration Generator")
    port = choose_port()
    channel = choose_channel()
    files = choose_files()
    output_midi = choose_output_midi()
    config_path = choose_config_path()

    config = {
        "port": port,
        "channel": channel + 1,  # store as 1-16
        "files": files,
        "output": output_midi
    }

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Configuration saved to {config_path}")


if __name__ == '__main__':
    main()

