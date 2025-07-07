#!/usr/bin/env python3
import json
import re
import argparse
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

# Map pitch names to semitone offsets within an octave
NOTE_NAMES = {
    'C': 0,  'C#': 1, 'D': 2,  'D#': 3,
    'E': 4,  'F': 5,  'F#': 6, 'G': 7,
    'G#': 8, 'A': 9,  'A#': 10,'B': 11
}

def note_to_number(note_str):
    """
    Convert a pitch string (e.g. 'C#4') to a MIDI note number.
    """
    match = re.fullmatch(r"([A-G]#?)(-?[0-9]+)", note_str.upper())
    if not match:
        raise ValueError(f"Invalid note: {note_str}")
    name, octave = match.groups()
    return NOTE_NAMES[name] + (int(octave) + 1) * 12


def main():
    parser = argparse.ArgumentParser(
        description="Convert one or more JSON song files into a single MIDI file"
    )
    parser.add_argument('config_json', help='Path to JSON config specifying files and output path')
    args = parser.parse_args()

    # Load configuration
    with open(args.config_json, 'r') as f:
        config = json.load(f)

    files = config.get('files')
    output_midi = config.get('output')
    if not files or not output_midi:
        raise ValueError("Config JSON must include 'files' (string or list) and 'output' path")
    if isinstance(files, str):
        files = [files]

    # Prepare MIDI file and track
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)
    pending_ticks = 0

    def flush(msg):
        nonlocal pending_ticks
        msg.time = pending_ticks
        pending_ticks = 0
        track.append(msg)

    # Process each JSON song file in order
    for idx, file_path in enumerate(files):
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Set tempo from first file
        if idx == 0:
            bpm = data.get('BPM', 120)
            tempo = bpm2tempo(bpm)
            track.append(MetaMessage('set_tempo', tempo=tempo, time=0))

        ticks_per_beat = data.get('ticks_per_beat', midi.ticks_per_beat or 480)
        midi.ticks_per_beat = ticks_per_beat

        # Iterate through events
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
                # Event-level rest
                if play is None:
                    pending_ticks += ticks
                    continue

                # Normalize play to base list
                if isinstance(play, (list, tuple)):
                    base_items = play
                else:
                    base_items = [play]

                # Build transposed sequence
                if rng and len(base_items) == 1 and isinstance(base_items[0], str):
                    base_note = note_to_number(base_items[0]) + transpose
                    length, offset = map(int, rng)
                    items = [base_note + i * offset for i in range(length)]
                else:
                    items = []
                    for item in base_items:
                        if item is None:
                            items.append(None)
                        else:
                            s = str(item)
                            if s.startswith('-'):
                                n = note_to_number(s.lstrip('-')) + transpose
                                items.append(f'-{n}')
                            else:
                                if isinstance(item, str):
                                    n0 = note_to_number(s)
                                else:
                                    n0 = int(item)
                                items.append(n0 + transpose)

                # Reverse if requested
                if reverse:
                    items = items[::-1]

                # Play sequence
                for it in items:
                    if it is None:
                        pending_ticks += ticks
                        continue
                    if isinstance(it, str) and it.startswith('-'):
                        n = int(it.lstrip('-'))
                        flush(Message('note_off', note=n, velocity=velocity))
                        pending_ticks += ticks
                    else:
                        n = int(it)
                        flush(Message('note_on', note=n, velocity=velocity))
                        if stop_flag:
                            pending_ticks += ticks
                            flush(Message('note_off', note=n, velocity=velocity))
                        else:
                            pending_ticks += ticks

    # Save MIDI file
    midi.save(output_midi)
    print(f"MIDI file saved to {output_midi}")

if __name__ == '__main__':
    main()
