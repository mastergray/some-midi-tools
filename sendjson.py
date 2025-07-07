#!/usr/bin/env python3
import json
import argparse
import time
import re
from mido import Message, open_output, bpm2tempo

NOTE_NAMES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3,
              'E': 4, 'F': 5, 'F#': 6, 'G': 7,
              'G#': 8, 'A': 9, 'A#': 10, 'B': 11}

def note_to_number(note_str):
    m = re.fullmatch(r"([A-G]#?)(-?[0-9]+)", note_str.upper())
    if not m:
        raise ValueError(f"Invalid note name: {note_str}")
    name, octave = m.groups()
    return NOTE_NAMES[name] + (int(octave) + 1) * 12


def play_song(data, port, channel):
    ticks_per_beat = data.get('ticks_per_beat', 480)
    bpm = data.get('BPM', 120)
    secs_per_tick = bpm2tempo(bpm) / 1e6 / ticks_per_beat

    pending = 0
    def send(msg):
        nonlocal pending
        if pending:
            time.sleep(pending * secs_per_tick)
        pending = 0
        if hasattr(msg, 'channel') and channel is not None:
            msg.channel = channel
        port.send(msg)

    for ev in data.get('SONG', []):
        repeat = int(ev.get('repeat', 0))
        play = ev.get('play')
        stop_flag = ev.get('stop', True)
        velocity = max(0, min(127, int(ev.get('velocity', 100))))
        duration = ev.get('time', 1)
        ticks = int((4 / duration) * ticks_per_beat)
        rng = ev.get('range')
        reverse = ev.get('reverse', False)
        if isinstance(reverse, str):
            reverse = reverse.lower() in ('true','1','yes')
        transpose = int(ev.get('transpose', 0))

        for _ in range(repeat + 1):
            if play is None:
                pending += ticks
                continue

            # Build sequence items, applying transpose immediately
            if rng and isinstance(play, str):
                base = note_to_number(play) + transpose
                length, offset = map(int, rng)
                items = [base + i * offset for i in range(length)]
            elif isinstance(play, str):
                items = [note_to_number(play) + transpose]
            else:
                items = []
                for item in play:
                    if item is None:
                        items.append(None)
                    else:
                        s = str(item)
                        if s.startswith('-'):
                            n = note_to_number(s.lstrip('-')) + transpose
                            items.append(f'-{n}')
                        else:
                            items.append(note_to_number(s) + transpose)

            # Reverse sequence if requested
            if reverse:
                items = items[::-1]

            # Play items
            for it in items:
                if it is None:
                    pending += ticks
                    continue
                if isinstance(it, str) and it.startswith('-'):
                    n = int(it.lstrip('-'))
                    send(Message('note_off', note=n, velocity=velocity))
                    pending += ticks
                else:
                    n = int(it)
                    send(Message('note_on', note=n, velocity=velocity))
                    if stop_flag:
                        pending += ticks
                        send(Message('note_off', note=n, velocity=velocity))
                    else:
                        pending += ticks


def main():
    p = argparse.ArgumentParser(description="Send one or more JSON songs to a MIDI port")
    p.add_argument('config_json', help='Config with port, channel, and files')
    args = p.parse_args()

    cfg = json.load(open(args.config_json))
    port_name = cfg.get('port')
    if not port_name:
        raise ValueError("Config JSON must include 'port'")
    ch = cfg.get('channel')
    channel = int(ch) - 1 if ch is not None else None

    files = cfg.get('files')
    if isinstance(files, str): files = [files]
    if not files:
        raise ValueError("Config JSON must include 'files'")

    with open_output(port_name) as port:
        for fp in files:
            data = json.load(open(fp))
            play_song(data, port, channel)

if __name__ == '__main__':
    main()
