import re
import language_tool_python

# Initialize the language tool as global instance
tool = None
FAST_MODE = True  # Set to False for more accurate but slower processing


def init_language_tool():
    global tool
    if not FAST_MODE and tool is None:
        tool = language_tool_python.LanguageTool('en-US')


def clean_text(text, use_language_tool=False):
    # Compile regex patterns for better performance
    CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]')
    STUCK_WORDS = re.compile(r'(?<=[a-z])(?=[A-Z])')

    # Fast initial cleanup
    text = CONTROL_CHARS.sub('', text)
    text = STUCK_WORDS.sub(' ', text)
    text = text.replace('|', 'I')

    # Split and clean lines
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append(line)
            continue

        # Apply language tool only if requested and not in fast mode
        if use_language_tool and not FAST_MODE and tool is not None:
            try:
                matches = tool.check(line)
                if matches:
                    for match in matches:
                        if match.replacements:
                            line = line[:match.offset] + match.replacements[0] + line[match.offset + match.errorLength:]
            except:
                pass  # Skip language checking if any error occurs

        cleaned_lines.append(line)

    # Join lines back together
    return '\n'.join(cleaned_lines)