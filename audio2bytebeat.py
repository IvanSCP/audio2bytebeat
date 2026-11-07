import argparse
import base64
import json
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

DOLLCHAN_URL = "https://dollchan.net/bytebeat/#v3b64"
B64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

FORMULA = (
    "((S,A,i=t%(S.length*.75|0),g=i/3|0,r=i%3,"
    "a=k=>Math.max(0,A.indexOf(S[4*g+k])))=>"
    "(a(0)<<18|a(1)<<12|a(2)<<6|a(3))>>16-8*r&255)"
    '("@DATA@","@ALPHABET@")'
)

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bytebeat</title>
</head>
<body>
<p>Redirecting to Dollchan Bytebeat Composer... If nothing happens, <a id="l" href="#">click here</a>.</p>
<script>
var u = "@URL@";
document.getElementById("l").href = u;
location.replace(u);
</script>
</body>
</html>
"""

EPILOG = """examples:
  python audio2bytebeat.py song.mp3
  python audio2bytebeat.py song.flac -f formula -t 8
  python audio2bytebeat.py voice.wav -f link -r 5512 -t 10
  python audio2bytebeat.py song.ogg -f html -s 30 -t 12 -o play.html
"""


def find_ffmpeg(custom=None):
    if custom:
        return custom
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found. Install it system-wide "
                 "or run: pip install imageio-ffmpeg")


def convert_to_u8(src, rate, start, duration, highpass, lowpass, normalize, ffmpeg):
    filters = []
    if highpass > 0:
        filters.append(f"highpass=f={highpass:g}")
    if lowpass > 0:
        if lowpass >= rate / 2:
            print(f"Warning: lowpass {lowpass:g} Hz is not below the Nyquist "
                  f"frequency ({rate / 2:g} Hz), filter disabled.", file=sys.stderr)
        else:
            filters.append(f"lowpass=f={lowpass:g}")
    if normalize:
        filters.append("loudnorm")

    cmd = [ffmpeg, "-v", "error", "-nostdin"]
    if start:
        cmd += ["-ss", f"{start:g}"]
    if duration:
        cmd += ["-t", f"{duration:g}"]
    cmd += ["-i", str(src), "-vn", "-sn", "-dn", "-ac", "1", "-ar", str(rate)]
    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd += ["-f", "u8", "-"]

    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        sys.exit("ffmpeg error:\n" + proc.stderr.decode(errors="replace"))
    if not proc.stdout:
        sys.exit("ffmpeg returned no data (check --start and --duration).")
    return proc.stdout


def make_formula(raw):
    b64 = base64.b64encode(raw).decode().rstrip("=")
    return FORMULA.replace("@DATA@", b64).replace("@ALPHABET@", B64_ALPHABET)


def make_link(code, rate):
    song = {"code": code, "sampleRate": rate, "mode": "Bytebeat"}
    js = json.dumps(song, separators=(",", ":")).encode("utf-8")
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = comp.compress(js) + comp.flush()
    return DOLLCHAN_URL + base64.b64encode(packed).decode().rstrip("=")


def make_html(url):
    return HTML_TEMPLATE.replace("@URL@", url)


def ask_format():
    print("Output type:\n"
          "  1) formula to paste into the site (.txt)\n"
          "  2) ready-made Dollchan link (.txt)\n"
          "  3) HTML file that redirects to Dollchan (.html)")
    variants = {"1": "formula", "2": "link", "3": "html"}
    while True:
        choice = input("Choice [1]: ").strip() or "1"
        if choice in variants:
            return variants[choice]
        print("Enter 1, 2 or 3.")


def main():
    ap = argparse.ArgumentParser(
        description="Convert audio to bytebeat for Dollchan Bytebeat Composer.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="audio file (any format ffmpeg can read)")
    ap.add_argument("-f", "--format", choices=["formula", "link", "html"],
                    help="output type: formula (.txt), link (.txt) or html; "
                         "asked interactively if omitted")
    ap.add_argument("-o", "--output", help="output file name")
    ap.add_argument("-r", "--rate", type=int, default=8000,
                    help="sample rate in Hz (default: 8000)")
    ap.add_argument("-t", "--duration", type=float, default=None,
                    help="length in seconds (default: whole file)")
    ap.add_argument("-s", "--start", type=float, default=0,
                    help="start offset in seconds (default: 0)")
    ap.add_argument("--highpass", type=float, default=40,
                    help="high-pass cutoff in Hz, 0 to disable (default: 40)")
    ap.add_argument("--lowpass", type=float, default=None,
                    help="low-pass cutoff in Hz, 0 to disable "
                         "(default: 3500 at 8000 Hz, 43.75%% of the rate otherwise)")
    ap.add_argument("--no-normalize", action="store_true",
                    help="disable loudnorm")
    ap.add_argument("--ffmpeg", help="path to the ffmpeg executable")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        sys.exit(f"File not found: {src}")
    if args.rate < 1000:
        sys.exit("Sample rate is too low (minimum 1000 Hz).")

    fmt = args.format
    if fmt is None:
        fmt = ask_format() if sys.stdin.isatty() else "formula"

    lowpass = args.lowpass if args.lowpass is not None else min(3500, args.rate * 0.4375)

    raw = convert_to_u8(src, args.rate, args.start, args.duration,
                        args.highpass, lowpass, not args.no_normalize,
                        find_ffmpeg(args.ffmpeg))
    seconds = len(raw) / args.rate
    print(f"Audio: {seconds:.1f} s, {args.rate} Hz, {len(raw) / 1024:.1f} KB of raw data")
    if len(raw) > 200_000:
        print("Warning: large amount of data, the site's editor may lag. "
              "Reduce --duration or --rate.", file=sys.stderr)

    code = make_formula(raw)
    if fmt == "formula":
        text, default_name = code, src.stem + ".txt"
    else:
        url = make_link(code, args.rate)
        if fmt == "link":
            text, default_name = url, src.stem + "_link.txt"
        else:
            text, default_name = make_html(url), src.stem + ".html"

    out = Path(args.output) if args.output else src.with_name(default_name)
    out.write_text(text, encoding="utf-8", newline="")
    print(f"Done: {out} ({len(text) / 1024:.1f} KB)")
    if fmt == "formula":
        print(f"On the site: Bytebeat mode, {args.rate} Hz, paste the file contents.")
    elif fmt == "link":
        print("Open the link from the file in a browser.")
    else:
        print("Open the .html file in a browser, it redirects to the site with the code loaded.")


if __name__ == "__main__":
    main()
