"""
Subtitle Converter Module

This module provides functionality to convert various subtitle formats to SRT format.
Supported formats include: SUB, ASS/SSA, TTML/DFXP/ITT, VTT, SBV, STL, and SMI.
"""

import os
import re
import texts
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List
from utils import detect_encoding


def convert_sub_to_srt(input_file: str, output_file: str) -> None:
    """Convert SUB subtitle file to SRT format.

    Args:
        input_file: Path to the input SUB file
        output_file: Path to the output SRT file
    """
    encoding = detect_encoding(input_file)

    try:
        with (
            open(input_file, "r", encoding=encoding, errors="replace") as sub,
            open(output_file, "w", encoding="utf-8") as srt,
        ):
            srt_counter = 1

            while True:
                line = sub.readline().strip()
                if not line:
                    break

                match = re.match(r"\{(\d+)\}\{(\d+)\}(.*)", line)
                if match:
                    start, end, text = match.groups()
                    text_lines = text.split("|")
                    formatted_start = format_sub_time(start)
                    formatted_end = format_sub_time(end)

                    srt.write(f"{srt_counter}\n")
                    srt.write(f"{formatted_start} --> {formatted_end}\n")
                    srt.write("\n".join(text_lines) + "\n\n")
                    srt_counter += 1
                else:
                    timestamps = line
                    text_lines = []

                    while True:
                        next_line = sub.readline().strip()
                        if not next_line:
                            break
                        text_lines.append(next_line.replace("[br]", "\n"))

                    if "," in timestamps:
                        start, end = timestamps.split(",")
                        formatted_start = format_sub_time(start)
                        formatted_end = format_sub_time(end)

                        srt.write(f"{srt_counter}\n")
                        srt.write(f"{formatted_start} --> {formatted_end}\n")
                        srt.write("\n".join(text_lines) + "\n\n")
                        srt_counter += 1
    except Exception as e:
        raise IOError(texts.ERROR_CONVERTING_SUBTITLE.format(error=str(e)))


def format_sub_time(time_str: str) -> str:
    """Format SUB time string to SRT time format.

    Args:
        time_str: Time string from SUB file

    Returns:
        Formatted time string in SRT format
    """
    if time_str.isdigit():
        ms = int(time_str) * 10
        s, ms = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    parts = re.split(r"[:.]", time_str)
    if len(parts) >= 4:
        h, m, s, ms = map(int, parts[:4])
        ms = ms * 10  # Convert to milliseconds
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    else:
        # Fallback for incomplete time format
        return "00:00:00,000"


def convert_ass_to_srt(input_file: str, output_file: str) -> None:
    """Convert ASS/SSA subtitle file to SRT format.

    Args:
        input_file: Path to the input ASS/SSA file
        output_file: Path to the output SRT file
    """
    encoding = detect_encoding(input_file)

    try:
        with (
            open(input_file, "r", encoding=encoding, errors="replace") as ass,
            open(output_file, "w", encoding="utf-8") as srt,
        ):
            srt_counter = 1
            buffer = ""
            collecting = False

            for line in ass:
                if line.startswith("Dialogue:"):
                    collecting = True
                    if buffer:
                        srt.write(f"{buffer}\n\n")
                        srt_counter += 1

                    parts = line.split(",", 9)
                    if len(parts) < 10:
                        continue

                    start = parts[1].strip()
                    end = parts[2].strip()
                    text = parts[9].replace("\\N", "\n").strip()

                    # Replace ASS/SSA tags with SRT tags
                    text = text.replace("{i}", "<i>").replace("{/i}", "</i>")
                    text = text.replace("{u}", "<u>").replace("{/u}", "</u>")
                    text = text.replace("{b}", "<b>").replace("{/b}", "</b>")

                    buffer = f"{srt_counter}\n{format_ass_time(start)} --> {format_ass_time(end)}\n{text}"
                elif collecting:
                    line = line.strip()
                    # Replace ASS/SSA tags with SRT tags
                    line = line.replace("{i}", "<i>").replace("{/i}", "</i>")
                    line = line.replace("{u}", "<u>").replace("{/u}", "</u>")
                    line = line.replace("{b}", "<b>").replace("{/b}", "</b>")
                    buffer += f"\n{line}"

            if buffer:
                srt.write(f"{buffer}\n\n")
    except Exception as e:
        raise IOError(texts.ERROR_CONVERTING_SUBTITLE.format(error=str(e)))


def format_ass_time(time_str: str) -> str:
    """Format ASS/SSA time string to SRT time format.

    Args:
        time_str: Time string from ASS/SSA file (H:MM:SS.CC format)

    Returns:
        Formatted time string in SRT format (HH:MM:SS,mmm)
    """
    t = time_str.split(":")
    hours = int(t[0])
    minutes = int(t[1])
    seconds = float(t[2])
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{int((seconds - int(seconds)) * 1000):03}"


def convert_ttml_or_dfxp_to_srt(input_file: str, output_file: str) -> None:
    """Convert TTML/DFXP subtitle file to SRT format.

    Args:
        input_file: Path to the input TTML/DFXP file
        output_file: Path to the output SRT file
    """
    try:
        with open(input_file, "rb") as file:
            data = file.read()
            encoding = detect_encoding(input_file)
            content = data.decode(encoding, errors="replace")
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(texts.ERROR_PARSING_XML.format(error=str(e)))
    except Exception as e:
        raise IOError(texts.ERROR_READING_FILE.format(error=str(e)))
    captions = [elem for elem in root.iter() if strip_namespace(elem.tag) == "p"]
    with open(output_file, "w", encoding="utf-8", errors="replace") as srt:
        for idx, caption in enumerate(captions, 1):
            begin = format_ttml_time(caption.attrib.get("begin"))
            end = format_ttml_time(caption.attrib.get("end"))

            def process_element(elem):
                text = ""
                tag = strip_namespace(elem.tag)
                end_tags = []
                # Handle start tags
                if tag == "br":
                    text += "\n"
                elif tag in ["b", "i", "u", "font"]:
                    text += f"<{tag}>"
                    end_tags.insert(0, f"</{tag}>")
                elif tag == "span":
                    style = elem.attrib.get("style", "")
                    styles = style.strip().lower().split()
                    for style_attr in styles:
                        if style_attr == "bold":
                            text += "<b>"
                            end_tags.insert(0, "</b>")
                        elif style_attr == "italic":
                            text += "<i>"
                            end_tags.insert(0, "</i>")
                        elif style_attr == "underline":
                            text += "<u>"
                            end_tags.insert(0, "</u>")
                    if "color" in elem.attrib:
                        color = elem.attrib["color"]
                        text += f'<font color="{color}">'
                        end_tags.insert(0, "</font>")
                # Add text content
                if elem.text:
                    text += elem.text
                # Recursively process child elements
                for child in elem:
                    text += process_element(child)
                # Handle end tags
                for end_tag in end_tags:
                    text += end_tag
                # Add tail text
                if elem.tail:
                    text += elem.tail
                return text

            # Process caption content
            text = process_element(caption)
            srt.write(f"{idx}\n")
            srt.write(f"{begin} --> {end}\n")
            srt.write(f"{text.strip()}\n\n")


def format_ttml_time(timestamp: str) -> str:
    """Format TTML timestamp to SRT time format.

    Args:
        timestamp: TTML timestamp string

    Returns:
        Formatted time string in SRT format
    """
    # Remove 's' suffix if present
    timestamp = timestamp.replace("s", "")
    # Check for SMPTE format HH:MM:SS:FF
    if timestamp.count(":") == 3:
        try:
            hours, minutes, seconds, frames = map(int, timestamp.split(":"))
            frame_rate = 25  # Adjust frame rate as needed
            milliseconds = int((frames / frame_rate) * 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        except ValueError:
            return timestamp
    # Check if already in HH:MM:SS format
    elif ":" in timestamp:
        return timestamp.replace(".", ",")
    # Convert from seconds to HH:MM:SS,mmm
    else:
        try:
            seconds = float(timestamp)
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")
        except ValueError:
            return timestamp


def convert_vtt_to_srt(input_file: str, output_file: str) -> None:
    """Convert VTT subtitle file to SRT format.

    Args:
        input_file: Path to the input VTT file
        output_file: Path to the output SRT file
    """
    try:
        with open(input_file, "rb") as vtt_file:
            vtt_data = vtt_file.read()
            encoding = detect_encoding(input_file)
        with (
            open(input_file, "r", encoding=encoding, errors="replace") as vtt,
            open(output_file, "w", encoding="utf-8") as srt,
        ):
            srt_counter = 1
            allowed_tags = ["b", "i", "u", "font"]
            tag_pattern = re.compile(r"</?(?!" + "|".join(allowed_tags) + r")\w+[^>]*>")
            for line in vtt:
                match = re.match(
                    r"(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})", line
                )
                if match:
                    start, end = match.groups()
                    srt.write(f"{srt_counter}\n")
                    srt.write(
                        f"{start.replace('.', ',')} --> {end.replace('.', ',')}\n"
                    )
                    srt_counter += 1
                    text = ""
                    while True:
                        try:
                            next_line = next(vtt).strip()
                        except StopIteration:
                            break
                        if not next_line:
                            break
                        cleaned_line = tag_pattern.sub("", next_line)
                        text += cleaned_line + "\n"
                    srt.write(f"{text.strip()}\n\n")
    except Exception as e:
        raise IOError(texts.ERROR_CONVERTING_SUBTITLE.format(error=str(e)))


def convert_sbv_to_srt(input_file: str, output_file: str) -> None:
    """Convert SBV subtitle file to SRT format.

    Args:
        input_file: Path to the input SBV file
        output_file: Path to the output SRT file
    """
    try:
        encoding = detect_encoding(input_file)
        with (
            open(input_file, "r", encoding=encoding, errors="replace") as sbv,
            open(output_file, "w", encoding="utf-8") as srt,
        ):
            srt_counter = 1
            allowed_tags = ["b", "i", "u", "font"]
            tag_pattern = re.compile(r"</?(?!" + "|".join(allowed_tags) + r")\w+[^>]*>")
            timestamp_pattern = re.compile(r"\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+")
            while True:
                timestamps = sbv.readline()
                if not timestamps:
                    break
                timestamps = timestamps.strip()
                if not timestamps or not timestamp_pattern.match(timestamps):
                    continue
                text_lines = []
                while True:
                    position = sbv.tell()
                    line = sbv.readline()
                    if not line:
                        break
                    line = line.strip()
                    if timestamp_pattern.match(line):
                        sbv.seek(position)
                        break
                    cleaned_line = tag_pattern.sub("", line)
                    text_lines.append(cleaned_line)
                if "," in timestamps:
                    start, end = timestamps.split(",")
                    srt.write(f"{srt_counter}\n")
                    srt.write(f"{format_sbv_time(start)} --> {format_sbv_time(end)}\n")
                    srt.write("\n".join(text_lines) + "\n\n")
                    srt_counter += 1
    except Exception as e:
        raise IOError(texts.ERROR_CONVERTING_SUBTITLE.format(error=str(e)))


def format_sbv_time(time_str: str) -> str:
    """Format SBV time string to SRT format.

    Args:
        time_str: Time string from SBV file

    Returns:
        Formatted time string in SRT format
    """
    h, m, s = time_str.split(":")
    s = s.replace(".", ",")
    return f"{int(h):02}:{int(m):02}:{s}"


def convert_stl_to_srt(input_file: str, output_file: str) -> None:
    """Convert STL subtitle file to SRT format.

    Args:
        input_file: Path to the input STL file
        output_file: Path to the output SRT file
    """
    try:
        with open(input_file, "rb") as stl:
            stl_data = stl.read()
            encoding = detect_encoding(input_file)
            lines = stl_data.decode(encoding, errors="replace").splitlines()
        with open(output_file, "w", encoding="utf-8", errors="replace") as srt:
            srt_counter = 1
            for line in lines:
                parts = line.strip().split(",", 2)  # Split only on the first two commas
                if len(parts) >= 3:
                    start = convert_stl_time(parts[0].strip())
                    end = convert_stl_time(parts[1].strip())
                    text = (
                        parts[2].strip().replace("| ", "\n").replace("|", "\n")
                    )  # Replace '|' with newline
                    if text:  # Ensure text is not empty
                        srt.write(f"{srt_counter}\n")
                        srt.write(f"{start} --> {end}\n")
                        srt.write(f"{text}\n\n")
                        srt_counter += 1
    except Exception as e:
        raise IOError(texts.ERROR_CONVERTING_SUBTITLE.format(error=str(e)))


def convert_stl_time(time_str: str) -> str:
    """Convert STL time format to SRT time format.

    Args:
        time_str: Time string from STL file

    Returns:
        Formatted time string in SRT format
    """
    h, m, s, f = map(int, time_str.split(":"))
    total_seconds = h * 3600 + m * 60 + s + f / 30
    ms = int((total_seconds - int(total_seconds)) * 1000)
    return f"{int(total_seconds)//3600:02}:{(int(total_seconds)%3600)//60:02}:{int(total_seconds)%60:02},{ms:03}"


def convert_smi_to_srt(input_file: str, output_file: str) -> None:
    """Convert SMI subtitle file to SRT format.

    Args:
        input_file: Path to the input SMI file
        output_file: Path to the output SRT file
    """
    encoding = detect_encoding(input_file)

    try:
        with open(input_file, "r", encoding=encoding, errors="replace") as smi:
            content = smi.read()

        # Extract all SYNC blocks with their timestamps
        sync_blocks = re.findall(
            r"<SYNC\s+Start=(\d+)(?:\s+[^>]*)?>(.*?)(?=<SYNC|</BODY|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if not sync_blocks:
            raise ValueError(texts.NO_VALID_SYNC_BLOCKS_FOUND_SMI)

        with open(output_file, "w", encoding="utf-8", errors="replace") as srt:
            srt_counter = 1

            for i, (start_ms_str, text_block) in enumerate(sync_blocks):
                start_ms = int(start_ms_str)

                # Calculate end time
                if i < len(sync_blocks) - 1:
                    end_ms = int(sync_blocks[i + 1][0])
                else:
                    # Default duration for the last subtitle
                    end_ms = start_ms + 5000

                # Skip empty blocks that only serve to clear previous text
                if not text_block.strip() or text_block.strip() == "&nbsp;":
                    continue

                # Extract text from P tags and clean HTML formatting
                clean_text = ""

                # Find all P tags in the text block
                p_tags = re.finditer(
                    r"<P[^>]*>(.*?)(?=</P>|$)", text_block, re.DOTALL | re.IGNORECASE
                )

                for match in p_tags:
                    # Get the content between <P> and </P>
                    p_content = match.group(1).strip()

                    if not p_content or p_content == "&nbsp;":
                        continue

                    # First, handle <br> tags by replacing with a special marker
                    # This ensures they're preserved during other HTML tag removal
                    p_content = re.sub(
                        r"<br\s*/?>|<BR\s*/?>", "\n", p_content, flags=re.IGNORECASE
                    )

                    # Remove other HTML tags but preserve their content
                    p_content = re.sub(r"<[^>]*>", "", p_content)

                    # Decode HTML entities
                    html_entities = {
                        "&nbsp;": " ",
                        "&lt;": "<",
                        "&gt;": ">",
                        "&amp;": "&",
                        "&quot;": '"',
                        "&#39;": "'",
                        "&hellip;": "...",
                        "&mdash;": "—",
                        "&ndash;": "–",
                        "&lsquo;": """,
                        '&rsquo;': """,
                        "&ldquo;": '"',
                        "&rdquo;": '"',
                    }

                    for entity, replacement in html_entities.items():
                        p_content = p_content.replace(entity, replacement)

                    # Clean up whitespace while preserving newlines
                    lines = p_content.split("\n")
                    cleaned_lines = []
                    for line in lines:
                        # Replace multiple spaces with a single space and trim
                        cleaned_line = re.sub(r"\s+", " ", line).strip()
                        if cleaned_line:  # Only add non-empty lines
                            cleaned_lines.append(cleaned_line)

                    p_content = "\n".join(cleaned_lines)

                    if p_content:
                        clean_text += p_content + "\n"

                clean_text = clean_text.strip()

                # Skip if there's no text content after cleaning
                if not clean_text:
                    continue

                # Format timestamps for SRT
                start_time = format_ms_to_srt_time(start_ms)
                end_time = format_ms_to_srt_time(end_ms)

                # Write SRT entry
                srt.write(f"{srt_counter}\n")
                srt.write(f"{start_time} --> {end_time}\n")
                srt.write(f"{clean_text}\n\n")
                srt_counter += 1

    except Exception as e:
        raise IOError(texts.ERROR_CONVERTING_SUB_TO_SRT.format(error=str(e)))


def format_ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format (HH:MM:SS,mmm).

    Args:
        ms: Time in milliseconds

    Returns:
        Formatted time string in SRT format
    """
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def strip_namespace(tag: str) -> str:
    """Remove namespace from XML tag name.

    Args:
        tag: XML tag name with potential namespace

    Returns:
        Tag name without namespace
    """
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def convert_to_srt(
    subtitle_file: str, output_dir: str
) -> Tuple[Optional[str], List[str]]:
    """Convert subtitle file to SRT format.

    Args:
        subtitle_file: Path to the input subtitle file
        output_dir: Directory to save the converted SRT file

    Returns:
        Tuple of (output_file_path, messages_list)
    """
    file_extension = os.path.splitext(subtitle_file)[-1].lower()
    original_base_name = os.path.basename(
        os.path.splitext(subtitle_file)[0]
    )  # Store original base name
    srt_file = os.path.join(output_dir, "converted_" + original_base_name + ".srt")
    messages = []

    converters = {
        ".ttml": convert_ttml_or_dfxp_to_srt,
        ".dfxp": convert_ttml_or_dfxp_to_srt,
        ".itt": convert_ttml_or_dfxp_to_srt,
        ".vtt": convert_vtt_to_srt,
        ".sbv": convert_sbv_to_srt,
        ".sub": convert_sub_to_srt,
        ".ass": convert_ass_to_srt,
        ".ssa": convert_ass_to_srt,
        ".stl": convert_stl_to_srt,
        ".smi": convert_smi_to_srt,
    }

    converter = converters.get(file_extension)
    if converter:
        try:
            messages.append(
                texts.CONVERTING_FORMAT_TO_SRT.format(format=file_extension.upper())
            )
            converter(subtitle_file, srt_file)
        except Exception as e:
            messages.append(texts.ERROR_CONVERTING_SUBTITLE.format(error=str(e)))
            return None, messages
        return srt_file, messages

    messages.append(
        texts.UNSUPPORTED_SUBTITLE_FORMAT_FOR_CONVERSION.format(
            extension=file_extension
        )
    )
    return None, messages
