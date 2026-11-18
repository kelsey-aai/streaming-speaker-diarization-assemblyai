# Streaming speaker diarization with AssemblyAI STT 3.7 Realtime

Companion code for the AssemblyAI blog post
[Streaming speaker diarization: how to identify who's speaking in real time](https://www.assemblyai.com/blog/streaming-speaker-diarization).

`diarize_stream.py` streams a WAV file to AssemblyAI's Streaming API with
`speech_model="assemblyai-stt-3-7-realtime"` and `speaker_labels=True`, then prints
each final turn with its speaker label. When a turn's words carry more than one
speaker (an interjection mid-turn), it also prints the word-level runs.

## How the labels behave

- Each final `Turn` carries a `speaker_label` (`A`, `B`, ...). Labels are final when
  the turn ends. There is no revision pass and no `SpeakerRevision` message.
- Each final word carries its own `speaker` field, so you can catch speaker
  changes inside a turn. The field can be absent on a word; the script falls back
  to the turn label.
- Turns with less than about 1 second of audio are labeled `PENDING`.
- `max_speakers` (1-10) is a hard cap: extra speakers are merged into the closest
  existing label. Leave a little headroom above the count you expect.

## Run it

Requires Python 3.9+ and a 16-bit mono PCM WAV file.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your key, then export it
export ASSEMBLYAI_API_KEY=your_api_key_here
python diarize_stream.py conversation.wav --max-speakers 3
```

Example output:

```text
Session started: 7f3a9c2e-...
[A] Good morning, thanks for joining the call.
[B] Good morning. Happy to be here.
[PENDING] Yeah.
[A] So let's start with a quick overview of the project timeline.
Session terminated: 41.2s of audio processed
```

To convert another file to 16 kHz mono WAV:

```bash
ffmpeg -i input.mp3 -ac 1 -ar 16000 -sample_fmt s16 conversation.wav
```

## Model choice

- `assemblyai-stt-3-7-realtime` ($0.30/hr) is the model the docs recommend for
  diarization: notetakers, meetings and live captions.
- `assemblyai-stt-3-7-realtime-agent` ($0.45/hr) also supports `speaker_labels`.
  Use it when a voice agent answers the speaker.

The script streams at real-time pace (50 ms chunks). Streaming is billed on
session duration, so the script always terminates the session when the file ends.

Docs: [Streaming diarization and multichannel](https://www.assemblyai.com/docs/streaming/label-speakers-and-separate-channels)

## License

MIT
