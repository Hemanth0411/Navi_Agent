# NewAgent

A Python-based agent framework for autonomous exploration and interaction with Android applications. This project is based on and inspired by [AppAgent](https://github.com/TencentQQGYLab/AppAgent), which automates interactions with Android apps using computer vision, UI element analysis, and NLP.

## Project Structure

```
NewAgent/
├── apps/ # Directory for app-specific data and documentation
│ ├── auto_docs/ # Generated documentation of app features
│ ├── demos/ # Exploration session data
│ │ ├── screenshots/ # UI screenshots during exploration
│ │ ├── xmls/ # UI hierarchy XML files
│ │ └── logs/ # Exploration and reflection logs
├── scripts/ # Core functionality scripts
│ ├── and_controller.py # Android device control and interaction
│ ├── config.py # Configuration management
│ ├── model.py # AI model integration
│ ├── prompts.py # AI model prompts
│ └── utils.py # Utility functions
├── config.yaml # Configuration settings
├── learn.py # Main script for autonomous exploration
├── requirements.txt # Project dependencies
└── LICENSE # MIT License
```

## Prerequisites

- Python 3.x
- Android Debug Bridge (ADB)
- Android device with USB debugging enabled or Android Studio emulator
- API key for your chosen AI model (Gemini, OpenAI, or Qwen)

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

### Autonomous App Exploration

Run the agent to explore an Android app:

```bash
python learn.py --package "com.example.app" --app_name "Example App" --description "This is a sample app for testing"
```

Or run interactively:
```bash
python learn.py
```
Then follow the prompts to enter:
- Package name (e.g., com.android.chrome)
- App name (e.g., Chrome)
- App description (e.g., "A web browser for Android devices")

### Features

- **Robust Error Handling**: Comprehensive error handling and recovery mechanisms
- **Intelligent Recovery**: Multiple recovery strategies for app crashes and stuck states
- **Feature Validation**: Strict validation of extracted features and actions
- **State Management**: Advanced state tracking and comparison
- **Action Validation**: Comprehensive validation of all action types and parameters
- **Memory Management**: Bounded exploration history to prevent memory issues
- **Multiple AI Models**: Support for Gemini, OpenAI, and Qwen
- **Configurable Parameters**: Customize exploration behavior and documentation

### Exploration Process

1. **App Launch**: The agent launches the target app using its package name
2. **Feature Understanding**: Uses the provided description to understand the app's purpose
3. **Systematic Exploration**: 
   - Identifies and interacts with UI elements
   - Explores different features and functionalities
   - Documents discovered features
4. **Recovery Mechanisms**:
   - Automatic detection of app crashes
   - Multiple recovery strategies (back navigation, home navigation, app relaunch)
   - Stuck state detection and recovery
5. **Safe Interruption**: Can be safely stopped at any time using Ctrl+C
6. **Documentation**: Generates comprehensive documentation of explored features

### Recovery Strategies

The agent implements multiple recovery strategies:
1. **Back Navigation**: Attempts to go back when stuck
2. **Home Navigation**: Returns to home screen if back navigation fails
3. **App Relaunch**: Relaunches the app if other recovery methods fail
4. **Alternative Navigation**: Explores unexplored areas when stuck
5. **State Verification**: Verifies app state after recovery attempts

### Output

The agent generates:
- Screenshots of UI interactions
- XML hierarchy files for UI analysis
- Exploration and reflection logs
- Feature documentation in the `auto_docs` directory

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
