[![Build Status](https://github.com/denizsafak/AutoSubSync/actions/workflows/app.yml/badge.svg)](https://github.com/denizsafak/AutoSubSync/actions)
[![GitHub Release](https://img.shields.io/github/v/release/denizsafak/AutoSubSync)](https://github.com/denizsafak/AutoSubSync/releases/latest)
[![Operating Systems](https://img.shields.io/badge/os-windows%20%7C%20linux%20%7C%20macos%20-blue)](https://github.com/denizsafak/AutoSubSync/releases/latest)
[![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/denizsafak/AutoSubSync/total?color=blue)](https://github.com/denizsafak/AutoSubSync/releases/latest)

# AutoSubSync: Automatic / Manual Subtitle Synchronization Tool
AutoSubSync is a Python-based application designed to effortlessly synchronize subtitle files by shifting them by a specified number of milliseconds or automatically syncing them. Whether you need to adjust subtitles for a movie or a video, this subtitle sync fixing tool offers a simple and intuitive interface to perform the task efficiently.

<img title="AutoSubSync" src='images/AutoSubSync1.png'> <img title="AutoSubSync" src='images/AutoSubSync2.png'> <img title="AutoSubSync" src='images/AutoSubSync3.png'> <img title="AutoSubSync" src='images/AutoSubSync4.png'>

> # [Download the Latest Release](https://github.com/denizsafak/AutoSubSync/releases/latest)
> You can download the latest executable version of AutoSubSync from this link.

## `How to Run?`
- Extract the zip.
- Run "AutoSubSync" file.

> MacOS users please read [this](#for-macososx-users).

## `Useage`
### Automatic Synchronization
- **Select Video/Reference subtitle and Subtitle Files:**
   - Drag and drop the video and subtitle files into the respective input boxes.
   - Alternatively, click on the input boxes to browse and select the files.
- **Choose Synchronization Tool:**
   - Select the synchronization tool (`ffsubsync` or `alass`) from the dropdown menu.-
- **Set Options:**
   - Configure additional options such as `Don't fix framerate`, `Use golden-section search`, and `Use auditok instead of WebRTC's VAD` for `ffsubsync`.
   - For `alass`, configure options like `Disable FPS guessing`, `Disable speed optimization`, and set the `Split Penalty`.
- **Select Output Location:**
   - Choose where to save the synchronized subtitle file using the dropdown menu.
- **Start Synchronization:**
   - Click the `Start Automatic Sync` button to begin the synchronization process.
- **Batch Mode:**
   - Enable batch mode to process multiple files at once. Drag and drop multiple files or folders into the batch input area.
   - You can also add `reference subtitle - subtitle` pairs in batch mode. Just try to add subtitles and it will ask you how you want to add them. You can add them as subtitles with [no video] or reference subtitles with [no subtitle] input.
   - Also, use `Auto-Pairing with Season/Episode` to automaticallty pair multiple subtitles with similar names. For example “S01E01 pairs with 01x01.
   - `Double click` any item to change them.
   - Use `del` key to delete any item.
     
### Manual Synchronization
- **Select Subtitle File:**
   - Drag and drop the subtitle file into the input box.
   - Alternatively, click on the input box to browse and select the file.
- **Set Time Shift:**
   - Enter the number of milliseconds to shift the subtitle. Use the `+` and `-` buttons to adjust the value.
- **Choose Output Option:**
   - Select whether to save the shifted subtitle to the desktop or replace the original subtitle file.
- **Start Shifting:**
   - Click the `Shift Subtitle` button to apply the time shift.
 
### Settings (Top Right Corner)
- Language: `English`, `Español`, `Deutsch`, `Français`, `Italiano`, `Polski`, `Português`, `Türkçe`, `Українська`, `Русский`, `中国人`, `日本語`, `한국어`, `हिन्दी`, `বাংলা`, `العربية`
- Theme: `System`, `Dark`, `Light`
- Change log window font: Configure the font used in log window. (Trigger log window to preview the changes)
- Log records and options: `Keep log records`, `Open logs folder` and `Clear all logs`
- Additional arguments for ffsubsync: Configure additional arguments for ffsubsync.
- Additional arguments for alass: Configure additional arguments for alass.
- Check video for subtitle stream in alass: Toggle for checking the subtitle streams in video for alass.
- Backup subtitles before overwriting: Toggle for creating a backup of subtitles before overwriting them.
- Keep converted subtitles: Toggle for keeping the converted subtitles after synchronization.
- Keep Extracted Subtitles: Toggle to keeping the extracted subtitles after synchronization.
- Remember the Changes: Toggle for remembering changes made.
- Reset to Default Settings: Restore settings to default values.

<img title="Auto-Pairing" src='images/Auto-Pairing.png'>

## `Features`
- “Auto-Pairing with Season/Episode” you can pair videos and reference subtitles with subtitles automatically using Season/Episode patterns like S01E01, 1x01, etc.
- Choose between alass and ffsubsync for automatic subtitle syncing.
- Batch processing for multiple video/reference subtitle and subtitle pairs.
- Support for different subtitle formats: .srt, .vtt, .sbv, .sub, .ass, .ssa, .dfxp, .ttml, .itt, .stl.
- Automatic Subtitle Synchronization: Automatically sync the subtitles with the video/reference subtitle, using [ffsubsync](https://github.com/smacke/ffsubsync) or [alass](https://github.com/kaegi/alass).
- Subtitle Shifting: Easily adjust subtitle timing by specifying the number of milliseconds to shift.
- Drag and Drop: Simply drag and drop subtitle and video files onto the interface to begin the synchronization process.
- Customization Options: Choose whether to save the shifted subtitle file to the desktop or replace the original file.
- Informative Messages: Receive clear feedback messages indicating the success or failure of the synchronization process.

## `For developers and contributors`
If you'd like to modify the code and contribute to development, you can download the [source code](https://github.com/denizsafak/AutoSubSync/archive/refs/heads/main.zip) and build it using build.py. Ensure Python is installed on your computer before proceeding. Also check [here](https://github.com/denizsafak/AutoSubSync/blob/main/main/resources/README.md).

## `For MacOS/OSX users:`
- You need to give permissions in "System Settings > Security & Privacy" to run the app.<br />
- You can use `brew install alass` command to make alass work.
- I haven't tested the `macos-arm64` build. Please open an issue if you face any problems.<br />

## `Credits`
Thanks to creators of [ffsubsync](https://github.com/smacke/ffsubsync), [alass](https://github.com/kaegi/alass), [ffmpeg](https://www.ffmpeg.org/) and others. The automatic subtitle syncing feature is possible because of ffsubsync and alass. This is just a GUI application that makes the process a bit easier. At the beginning, it was just a manual subtitle syncing program. Now it can do both manual and automatic subtitle sync.

Icon: [Subtitles icons created by Freepik - Flaticon](https://www.flaticon.com/free-icons/subtitles)

> [!IMPORTANT]
> The automatic sync feature is not always perfect. I recommend you to check the subtitle after syncing.

> Tags: automatic subtitle synchronization, autosubsync, automatic sub sync, subtitle synchronization, subtitle shifter, subtitle adjuster, subtitle tools, subtitle utilities, synchronize subtitles, adjust subtitle timing, subtitle management, Python subtitle tool, subtitle manipulation, subtitle synchronization script, subtitle sync fixing, subtitle sync fix, fix subtitle sync.
