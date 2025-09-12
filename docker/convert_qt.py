#!/usr/bin/env python3
"""
Script to convert PyQt6 imports to PySide6 imports for Docker compatibility
"""

import os
import re
import glob

def convert_pyqt6_to_pyside6(file_path):
    """Convert PyQt6 imports to PySide6 in a given file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Store original content for comparison
        original_content = content
        
        # Replace PyQt6 imports with PySide6
        content = re.sub(r'from PyQt6\.', 'from PySide6.', content)
        content = re.sub(r'import PyQt6\.', 'import PySide6.', content)
        
        # Replace PyQt6-specific signal syntax (pyqtSignal -> Signal)
        content = re.sub(r'pyqtSignal', 'Signal', content)
        
        # Fix the main.py ffmpeg path issue
        if file_path.endswith('main.py'):
            # Add safe path handling for FFMPEG_EXECUTABLE and FFPROBE_EXECUTABLE
            ffmpeg_path_fix = """# Set environment variables for ffmpeg and ffprobe
# Handle None values safely for Docker environment
ffmpeg_dir = os.path.dirname(FFMPEG_EXECUTABLE) if FFMPEG_EXECUTABLE else ""
ffprobe_dir = os.path.dirname(FFPROBE_EXECUTABLE) if FFPROBE_EXECUTABLE else ""
os.environ["PATH"] = os.pathsep.join(
    [
        ffmpeg_dir,
        ffprobe_dir,
        os.environ.get("PATH", ""),
    ]
)"""
            
            # Replace the problematic section
            old_pattern = r'# Set environment variables for ffmpeg and ffprobe\n.*?os\.environ\["PATH"\] = os\.pathsep\.join\(\s*\[\s*os\.path\.dirname\(FFMPEG_EXECUTABLE\),\s*os\.path\.dirname\(FFPROBE_EXECUTABLE\),\s*os\.environ\.get\("PATH", ""\),\s*\]\s*\)'
            content = re.sub(old_pattern, ffmpeg_path_fix, content, flags=re.DOTALL)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Converted: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to convert all Python files in the current directory"""
    # Find all Python files in the main directory
    python_files = glob.glob('/app/main/*.py')
    
    converted_count = 0
    total_files = 0
    
    for file_path in python_files:
        # Skip our compatibility files
        if file_path.endswith(('qt_compat.py', 'convert_qt.py')):
            continue
            
        total_files += 1
        if convert_pyqt6_to_pyside6(file_path):
            converted_count += 1
    
    print(f"\nConversion complete!")
    print(f"Files processed: {total_files}")
    print(f"Files converted: {converted_count}")
    
    # Add PySide6 import at the top of utils.py for signal import
    utils_path = '/app/main/utils.py'
    if os.path.exists(utils_path):
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'from PySide6.QtCore import Signal' not in content:
            # Add Signal import at the top after existing PySide6 imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'from PySide6.QtCore import' in line and 'Signal' not in line:
                    if 'Signal' not in line:
                        lines[i] = line.rstrip() + ', Signal'
                    break
            
            content = '\n'.join(lines)
            with open(utils_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Added Signal import to utils.py")

if __name__ == '__main__':
    main()
