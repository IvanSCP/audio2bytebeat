# audio2bytebeat

Converts an audio file into a bytebeat formula for Dollchan Bytebeat Composer (https://dollchan.net/bytebeat/).

The audio is downmixed to mono, resampled, quantized to 8-bit unsigned PCM and embedded into the formula as a base64 string. The formula decodes it on the fly, so it works in the site's sandboxed player. This is a sample player in a bytebeat wrapper, not a transcription of the music into a formula, so the size grows linearly with the length. Short clips of 5 to 15 seconds at 8000 Hz are practical.

## Web version

No installation needed, everything runs in your browser and the file is not uploaded anywhere:

https://ivanscp.github.io/audio2bytebeat/

The source is in the docs folder of this repository.

## Python script

Requirements: Python 3.7 or newer and ffmpeg. If ffmpeg is not in your PATH, install it through pip:

```
pip install imageio-ffmpeg
```

Usage:

```
python audio2bytebeat.py input.mp3
```

Any format that ffmpeg can read works. If you do not pass -f, the script asks what to produce. Output types:

formula: the formula to paste into the site, saved as name.txt
link: a ready-made Dollchan link, saved as name_link.txt
html: an HTML page that redirects to Dollchan with the code loaded, saved as name.html

The HTML file is useful when the link is too long to paste into the address bar.

Examples:

```
python audio2bytebeat.py input.mp3
python audio2bytebeat.py song.flac -f formula -t 8
python audio2bytebeat.py voice.wav -f link -r 5512 -t 10
python audio2bytebeat.py song.ogg -f html -s 30 -t 12 -o play.html
```

Options:

```
-f, --format       formula, link or html
-o, --output       output file name
-r, --rate         sample rate in Hz, default 8000
-t, --duration     length in seconds, default whole file
-s, --start        start offset in seconds, default 0
--highpass         high-pass cutoff in Hz, default 40, 0 disables
--lowpass          low-pass cutoff in Hz, 0 disables
--no-normalize     disable loudnorm
--ffmpeg           path to the ffmpeg executable
```

The default low-pass is 3500 Hz at 8000 Hz. For other sample rates it is 43.75 percent of the rate, which keeps it below the Nyquist frequency.

## Using the result

On the Dollchan site choose the Bytebeat mode, set the same sample rate that you used for the conversion (8000 Hz by default), paste the formula into the code field and press play. For the link and html outputs just open them in a browser, the mode and the sample rate are already included.

## Notes

The web version normalizes the peak level instead of using loudnorm, and it does the filtering and resampling with the Web Audio API, so its output is very close to the script's but not identical. Which input formats it accepts depends on your browser.

Long files produce a lot of data and the editor may lag. Reduce the length or the sample rate if that happens.
