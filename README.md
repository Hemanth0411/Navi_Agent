# NewAgent

A Python-based agent framework for autonomous exploration and interaction with Android applications.

## Project Structure

```
NewAgent/
├── apps/               # Directory for app-specific data and documentation
├── scripts/           # Core functionality scripts
│   ├── and_controller.py
│   ├── config.py
│   ├── model.py
│   ├── prompts.py
│   └── utils.py
├── config.yaml        # Configuration settings
├── learn.py          # Main script for autonomous exploration
├── requirements.txt   # Project dependencies
└── LICENSE           # MIT License
```

## Prerequisites

- Python 3.x
- Android Debug Bridge (ADB)
- Android device with USB debugging enabled or Android Studio emulator

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd NewAgent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to set up your environment:

```yaml
MODEL: Gemini  # Options: Gemini, OpenAI, Qwen
GEMINI_API_KEY: "your-api-key"
GEMINI_MODEL_NAME: "gemini-1.5-flash"
ANDROID_SCREENSHOT_DIR: /sdcard/
ANDROID_XML_DIR: /sdcard/
DOC_REFINE: true
MAX_ROUNDS: 20
DARK_MODE: false
MIN_DIST: 10
```

## Usage

### Autonomous Exploration

Run the agent in autonomous exploration mode:

```bash
python learn.py --app [app_name]
```

Optional arguments:
- `--app`: Name of the target application to explore
- `--root_dir`: Root directory for agent operation (default: current directory)

## Features

- Autonomous exploration of Android applications
- Support for multiple AI models (Gemini, OpenAI, Qwen)
- Android device interaction through ADB
- Configurable exploration parameters
- Documentation generation for explored apps

## Dependencies

- argparse
- colorama
- dashscope
- opencv-python
- pyshine
- pyyaml
- requests
- google-generativeai
- Pillow

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
