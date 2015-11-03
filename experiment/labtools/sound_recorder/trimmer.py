import pydub
import unipath

originals = unipath.Path('sounds').listdir('*.wav')
trimmed_dir = unipath.Path('trimmed')

if not trimmed_dir.isdir():
    trimmed_dir.mkdir()

front_trim_ms = 800
back_trim_ms = 400

for sound_wav in originals:
    audio_segment = pydub.AudioSegment.from_wav(sound_wav)
    trimmed = audio_segment[front_trim_ms:-back_trim_ms]
    trimmed.export(unipath.Path(trimmed_dir, sound_wav.name))
