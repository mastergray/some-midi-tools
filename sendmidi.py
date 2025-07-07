#!/usr/bin/env python3
import json
import argparse
from mido import MidiFile, open_output

def main():
    parser = argparse.ArgumentParser(
        description="Play a MIDI file through a specified port and channel from a unified config"
    )
    parser.add_argument(
        'config_json',
        help='Path to the JSON config specifying port, channel, and output MIDI file'
    )
    args = parser.parse_args()

    # Load playback configuration
    with open(args.config_json, 'r') as f:
        config = json.load(f)

    port_name = config.get('port')
    if not port_name:
        raise ValueError("Config JSON must include 'port'")

    # Convert channel from 1-16 to 0-15
    channel = None
    if 'channel' in config:
        ch = int(config['channel'])
        if not 1 <= ch <= 16:
            raise ValueError("'channel' must be an integer 1–16")
        channel = ch - 1

    output_mid = config.get('output')
    if not output_mid:
        raise ValueError("Config JSON must include 'output' MIDI file path")

    # Open the output port and play the MIDI file
    with open_output(port_name) as port:
        mid = MidiFile(output_mid)
        for msg in mid.play():
            if hasattr(msg, 'channel') and channel is not None:
                msg.channel = channel
            port.send(msg)

if __name__ == '__main__':
    main()
