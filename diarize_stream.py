"""Stream a WAV file to AssemblyAI STT 3.7 Realtime with real-time speaker labels.

Prints one line per final turn, prefixed with the turn's speaker label, and
flags turns where the speaker changes mid-turn at the word level.

Usage:
    export ASSEMBLYAI_API_KEY=your_key
    python diarize_stream.py conversation.wav --max-speakers 3
"""

import argparse
import os
import time
import wave

from assemblyai.streaming.v3 import (
    BeginEvent,
    RealTimeError,
    RealTimeEvents,
    RealTimeParameters,
    RealTimeTranscriber,
    RealTimeTranscriberOptions,
    TerminationEvent,
    TurnEvent,
)

CHUNK_MS = 50  # the docs recommend 50 to 100 ms chunks


def speaker_runs(event: TurnEvent):
    """Group a final turn's words into consecutive runs by word-level speaker."""
    runs = []
    for word in event.words or []:
        # `speaker` only appears on final words and can be absent.
        # Fall back to the turn-level label when it is missing.
        speaker = word.speaker or event.speaker_label or "PENDING"
        if runs and runs[-1][0] == speaker:
            runs[-1][1].append(word.text)
        else:
            runs.append((speaker, [word.text]))
    return [(speaker, " ".join(words)) for speaker, words in runs]


def on_begin(client: RealTimeTranscriber, event: BeginEvent):
    print(f"Session started: {event.id}")


def on_turn(client: RealTimeTranscriber, event: TurnEvent):
    # Partials re-transcribe the turn as it grows. Act on finals.
    if not event.end_of_turn or not event.transcript:
        return

    label = event.speaker_label or "PENDING"
    print(f"[{label}] {event.transcript}")

    runs = speaker_runs(event)
    known = {speaker for speaker, _ in runs if speaker != "PENDING"}
    if len(known) > 1:
        for speaker, text in runs:
            print(f"    word-level [{speaker}] {text}")


def on_terminated(client: RealTimeTranscriber, event: TerminationEvent):
    print(f"Session terminated: {event.audio_duration_seconds}s of audio processed")


def on_error(client: RealTimeTranscriber, error: RealTimeError):
    print(f"Error: {error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("wav_path", help="16-bit mono PCM WAV file")
    parser.add_argument("--max-speakers", type=int, default=None)
    args = parser.parse_args()

    with wave.open(args.wav_path, "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise SystemExit("Expected a 16-bit mono WAV file.")
        sample_rate = wav.getframerate()
        frames_per_chunk = int(sample_rate * CHUNK_MS / 1000)

        client = RealTimeTranscriber(
            RealTimeTranscriberOptions(terminate_timeout=30.0),
            api_key=os.environ["ASSEMBLYAI_API_KEY"],
        )
        client.on(RealTimeEvents.Begin, on_begin)
        client.on(RealTimeEvents.Turn, on_turn)
        client.on(RealTimeEvents.Termination, on_terminated)
        client.on(RealTimeEvents.Error, on_error)

        client.connect(
            RealTimeParameters(
                sample_rate=sample_rate,
                speech_model="assemblyai-stt-3-7-realtime",
                speaker_labels=True,
                max_speakers=args.max_speakers,
            )
        )

        try:
            while True:
                chunk = wav.readframes(frames_per_chunk)
                if not chunk:
                    break
                client.stream(chunk)
                time.sleep(CHUNK_MS / 1000)  # real-time pace, like a live source
        finally:
            # Terminate finalizes the open turn before the session closes.
            client.disconnect(terminate=True)


if __name__ == "__main__":
    main()
