
Plan:
  -  `ffmpeg` and `ffprobe` comes embedded in [ffsubsync-bin](https://github.com/qwqcode/ffsubsync-bin). AutoSubSync also includes them, so there are duplicates. To save some filesize, I tried to create ffsubsync-bin that doesn't inclue ffmpeg binaries but didn't seem to work. It needs a fix.

Instructions:
  1) Run ffpmpeg_download.py, it will download the correct ffmpeg and ffprobe in `ffmpeg-bin` folder.
  2) Create a folder called `ffsubsync-bin`. Download latest ffsubsync from [here](https://github.com/qwqcode/ffsubsync-bin), rename it to "ffsubsync.exe". (if Windows)

Credits:
ffpmpeg_download.py and ffsubsync-bin is copied from [@qwqcode](https://github.com/qwqcode)'s [ffsubsync-bin](https://github.com/qwqcode/ffsubsync-bin)

```
Current Alass version: Alass 2
GitHub: https://github.com/kaegi/alass/releases/tag/v2.0.0
Release Date: Oct 10, 2019
If new version of alass releases, please just replace "/alass-bin/alass-cli.exe" with the new one.
```

```
Current ffsubsync version: v0.4.26
GitHub: https://github.com/qwqcode/ffsubsync-bin/releases/tag/v0.4.26
Release Date: Nov 18, 2024
If new version of ffsubsync releases, please just replace "/ffsubsync-bin/ffsubsync.exe" with the new one.
```
