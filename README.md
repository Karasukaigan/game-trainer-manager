# Game Trainer Manager

English | [简体中文](./README_ZH.md)

<img src="app/resources/logo.png" alt="Logo" width="200" height="200">

**Game Trainer Manager** is a lightweight software designed for managing `.exe` format game trainer files. It provides functions for downloading, saving, deleting, and more. The application supports both Simplified Chinese and English languages. It is completely free and open-source (please do not use it for commercial purposes).

## Features

- Manage `.exe` format game trainers
- Download, save, and delete trainers
- Multi-language support (Simplified Chinese and English)
- Lightweight
- Free and open-source

![screenshot](app/resources/screenshot_en.png)

## Installation

You can download the software in two ways:

1. **Directly from Releases:**
   - Go to the [Releases](https://github.com/Karasukaigan/game-trainer-manager/releases) section and download the installer.

2. **Clone the repository and run locally:**
   - Clone the repository to your local machine:
     ```bash
     git clone https://github.com/Karasukaigan/game-trainer-manager.git
     ```
   - Navigate to the project root directory and run the following commands:

     ```bash
     # Create a virtual environment named 'venv'
     python -m venv venv

     # Activate the virtual environment
     venv\Scripts\activate

     # Install the required dependencies
     pip install -r requirements.txt

     # Run the application
     python .\main.py
     ```

## Main Technology Stack

- **PyQt6**: Used to build the GUI framework.
- **requests + retrying + beautifulsoup4**: Used for updating.
- **gettext**: Used to implement multi-language UI pages.
- **PyInstaller**: Used to package Python programs into executable files.
- **Inno Setup**: Used for creating installation packages.

## Debug Mode

Locate the `config.ini` file in the project's root directory or the software's `_internal` directory, then change
```
debugmode = false
```
to
```
debugmode = true
```
to enable debug mode.

## Disclaimer

This project is created by players voluntarily and has no association with FLiNG Trainer. Its design purpose is to manage game trainer files in any .exe format, including but not limited to those created by FLiNG Trainer. This software is completely free and open-source, and should not be used for commercial purposes. The software developers are not responsible for any losses caused by the use of this software.  

This software respects the copyright of game trainer creators such as FLiNG Trainer, and will not make any modifications to the game trainer files except for renaming. It only provides management functions such as downloading, saving, and deleting.  

Furthermore, users should bear the risks associated with downloading and using third-party game trainers. Please ensure that you comply with the relevant game's terms of use and service agreement when using trainers. Developers are not responsible for any consequences arising from violating game company policies.  

This software is strictly prohibited from being used for any illegal purposes, including but not limited to violating game company policies, cheating, disrupting game balance, etc. Users should abide by relevant laws and regulations and game company policies when using this software to ensure a fair and legal gaming environment.  