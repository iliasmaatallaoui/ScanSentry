# ScanSentry

A lightweight Python utility that uses OCR (Optical Character Recognition) to monitor a specific region of your screen, detect predefined text, and automatically trigger keyboard actions. Originally developed for Metal Gear Solid V to identify and quarantine soldiers based on language skills, but adaptable for various automation needs.

## Features

- **Region Selection**: Define a specific screen area to monitor
- **OCR Detection**: Automatically detect and respond to text content in the selected region
- **Automated Controls**: Press configured keys when target text is found
- **Visual Overlay**: Display a border around the monitored region
- **Headless Mode**: Run without a GUI for minimal interference
- **Configurable**: Save and load your settings for easy reuse
- **Hotkey Control**: Full keyboard control with function key shortcuts

## Use Cases

- **MGSV Soldier Management**: Identify and quarantine soldiers with specific skills or language capabilities
- **Form Automation**: Detect specific form states and trigger actions
- **Game Assistance**: Monitor game UI elements and respond to specific conditions
- **Data Extraction**: Automatically scan and collect text information from applications

## Requirements

- Python 3.6+
- Tesseract OCR
- Python packages: see `requirements.txt`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/username/ScanSentry.git
cd ScanSentry
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract):
   - **Windows**: Download and install from [here](https://github.com/UB-Mannheim/tesseract/wiki)
   - **Linux**: `sudo apt install tesseract-ocr`
   - **Mac**: `brew install tesseract`

4. Update the Tesseract OCR path in the script if not using the default Windows location.

## Usage

### With GUI

```bash
python ScanSentry.py
```

### Headless Mode

```bash
python ScanSentry.py --headless --config settings.conf
```

## Keyboard Shortcuts

| Key | Function |
|-----|----------|
| F7  | Set top-left corner of the monitored region |
| F8  | Set bottom-right corner of the monitored region |
| F9  | Start scanning |
| F10 | Stop scanning |
| F11 | Toggle region overlay |
| F12 | Emergency exit (headless mode only) |

## Configuration

Create a configuration file to save your settings:

```
top_left=100,100
bottom_right=500,500
target_words=AT,S
```

You can modify `TARGET_WORDS` in the code or configuration file to search for different text.

## Customization

### Changing Target Words

Modify the `TARGET_WORDS` list to detect different text:

```python
TARGET_WORDS = ["AT", "S"]  # Default: Finds soldiers with these skills/ranks
```

### Changing Actions

When target text is found, the default action is to press the 'G' key (for selection in MGSV) and then press 'down' to move to the next soldier. Modify the `check_screen_and_act()` function to change this behavior:

```python
def check_screen_and_act(region):
    # ...
    if found_any:
        # Change 'g' to any key you want to press when text is found
        pyautogui.press('g')
    # Change or remove this to modify navigation behavior
    pyautogui.press('down')
```

## How It Works

1. Select a region of your screen to monitor
2. ScanSentry takes periodic screenshots of that region
3. OCR processes the image to extract text
4. If any target words are found, the script triggers the configured key press
5. The script continues scanning until stopped

## Troubleshooting

- **OCR Not Working**: Ensure Tesseract is installed and the path is correct
- **Hotkeys Not Responding**: Check for conflicts with other applications
- **Poor Text Recognition**: Adjust the preprocessing parameters for better results:
  ```python
  def preprocess_image(image):
      gray = ImageOps.grayscale(image)
      # Try adjusting the threshold (160) for better results
      return gray.point(lambda x: 0 if x < 160 else 255, '1')
  ```

## License

MIT License - See LICENSE file for details

## Acknowledgments

- This tool uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text recognition
- Inspired by the need to automate soldier management in Metal Gear Solid V

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Note: This tool is not affiliated with or endorsed by Konami or the Metal Gear Solid franchise.*
