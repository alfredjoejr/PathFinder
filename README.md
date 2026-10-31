# PathFinder 🎮🚗💨

**PathFinder** is an autonomous hardware-in-the-loop gaming robotics system. It processes live video streams (either captured from an external PC's display via USB camera or rendered locally) using Computer Vision (OpenCV), makes real-time steering/navigation decisions, and controls physical gaming hardware (a steering wheel driven by a stepper motor and gamepads driven by RC servos) through an ESP32 microcontroller over USB serial.

---

## 📑 Table of Contents

- [System Architecture](#system-architecture)
- [Hardware Setup & Wiring](#hardware-setup--wiring)
- [Supported Games & Modes](#supported-games--modes)
  - [1. Trackmania (Fully Autonomous)](#1-trackmania-fully-autonomous)
  - [2. Racing (Autonomous Car Game)](#2-racing-autonomous-car-game)
  - [3. Valorant (Auto-Aim & Navigation)](#3-valorant-auto-aim--navigation)
  - [4. Pac-Man (Manual & Autonomous)](#4-pac-man-manual--autonomous)
- [Serial Communication Protocol](#serial-communication-protocol)
- [Installation & Getting Started](#installation--getting-started)
- [How to Run](#how-to-run)
- [Project Directory Structure](#project-directory-structure)
- [Safety Features](#safety-features)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Display / Screen                       │
│  (Running Trackmania, Valorant, or Local Pac-Man Arcade)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Visual Feed)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    USB Web Camera Feed                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (OpenCV Frame Processing)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   PathFinder PC Brain                       │
│  - Launcher Control Center (main.py)                        │
│  - CV Engines (Lane detection, Canny edge density, HSV)     │
│  - PD Steering, Curvature, and Motion Planning Algorithms   │
│  - Serial Protocol Handler (actuator_controller.py)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ (USB Serial @ 115200 Baud)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  ESP32 Microcontroller                      │
│                (ActuatorProgram Firmware)                   │
├──────────────────────────────┬──────────────────────────────┤
│  STEP / DIR Pulses (PWM)     │  16-bit PWM Servo Channels   │
└──────────────┬───────────────┴──────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐ ┌───────────────────────────┐
│   NEMA Stepper Motor         │ │      5x MG996R Servos     │
│   (Steering Wheel Drive)     │ │  (Left/Right Sticks & RT) │
└──────────────────────────────┘ └───────────────────────────┘
```

---

## Hardware Setup & Wiring

The ESP32 microcontroller controls 1 stepper driver (e.g. A4988 / DRV8825) for high-torque steering wheel rotation and up to 5 PWM servos for gamepad joysticks and trigger buttons.

### Pinout Mapping

| Component | ESP32 GPIO | Function / Channel | Default / Neutral |
| :--- | :--- | :--- | :--- |
| **Stepper STEP** | `GPIO 4` | Step pulse generation (10–2000 Hz) | `STOP` |
| **Stepper DIR** | `GPIO 2` | Steering direction (High = Right, Low = Left) | `LOW` |
| **Servo 0 (LJX)** | `GPIO 25` | Left Joystick X (Strafe / Steering) | `90°` |
| **Servo 1 (LJY)** | `GPIO 26` | Left Joystick Y (Throttle / Walk Forward-Back) | `90°` |
| **Servo 2 (RJX)** | `GPIO 27` | Right Joystick X (Aim Left-Right) | `90°` |
| **Servo 3 (RJY)** | `GPIO 32` | Right Joystick Y (Aim Up-Down) | `90°` |
| **Servo 4 (TRIG)** | `GPIO 33` | Trigger / Fire / Gas Pedal Button | `0°` (Release) / `180°` (Pressed) |

> ⚠️ **Power Tip:** Power all servos and stepper motors with an external regulated 5V–6V high-current power supply (minimum 3A–5A). **Do NOT** power servos directly from the ESP32's 3.3V/VIN pins. Ensure common ground (`GND`) is shared between the power supply and ESP32.

---

## Supported Games & Modes

### 1. Trackmania (Fully Autonomous)
* **Location:** [`trackmania/trackmania_runner.py`](trackmania/trackmania_runner.py)
* **Target:** Played on a secondary computer with a camera pointed at the screen.
* **Computer Vision Pipeline:**
  * Real-time road segmentation using CIELAB color-distance thresholding with connected component analysis.
  * Alternative Canny edge-density corridor estimation mode.
  * 8-scanline weighted centerline extraction with adjustable lookahead.
* **Actuation:**
  * Closed-loop estimated position control for the stepper steering wheel (`STEPPER,LEFT/RIGHT`).
  * Optional servo left-joystick steering mode (`SERVO,LJX`).
  * Auto-throttle via trigger servo 4 with curvature-based braking.
  * Stuck-car watchdog notification if zero screen motion is detected for >3 seconds.

### 2. Racing (Autonomous Car Game)
* **Location:** [`racing/racing_runner.py`](racing/racing_runner.py)
* **Target:** Top-down / third-person racing games.
* **Computer Vision Pipeline:**
  * Horizontal ROI slicing (ignoring sky & vehicle HUD).
  * 3-zone Canny edge-density comparison (**Left**, **Center**, **Right**).
  * Steers toward the side with the clearest lane corridor with proportional stepping frequency (150–800 Hz).

### 3. Valorant (Auto-Aim & Navigation)
* **Location:** [`mapper/valorant_runner.py`](mapper/valorant_runner.py) & [`mapper/mapRunner.py`](mapper/mapRunner.py)
* **Target:** FPS navigation & physical gamepad control.
* **Pipeline:**
  * Visual lane corridor detection.
  * Right Joystick (`RJX`) proportional offset aiming toward open areas.
  * Left Joystick (`LJY`) forward navigation.
  * Offline A* pathfinding and map coordinate translation via `mapRunner.py`.

### 4. Pac-Man (Manual & Autonomous)
* **Location:** [`pacman/pacman_game.py`](pacman/pacman_game.py) & [`pacman/pacman_runner.py`](pacman/pacman_runner.py)
* **Modes:**
  * **Manual Mode:** Standalone Pygame recreation with complete arcade mechanics, ghost house pen exit, and scatter/chase states. Steer with `WASD` / `Arrow Keys`.
  * **Auto Mode:** Screen capture / Camera feed tracking Pac-Man centroid via HSV color isolation and probing 4 directional corridors to physical Left Joystick (`LJX`, `LJY`) servo positions.

---

## Serial Communication Protocol

The PC communicates with the ESP32 over USB Serial at **`115200 Baud`** using newline-terminated text strings.

### 1. State Machine Commands (PC → ESP32)
```text
MODE,SET,VALORANT\n    # Set active game to VALORANT
MODE,SET,RACING\n      # Set active game to RACING
MODE,START\n           # Transition state to RUNNING
MODE,STOP\n            # Return actuators to neutral and state to STOPPED
MODE,RESET\n           # Return state to IDLE (allows switching modes)
MODE,STATUS\n          # Request current mode & state
```

### 2. Servo Actuation (PC → ESP32)
*Valid only when in `RUNNING` state.*
```text
SERVO,LJX,LJY,RJX,RJY,TRIGGER[,DURATION]\n
```
* **Parameters:**
  * `LJX`, `LJY`, `RJX`, `RJY`: `0` to `180` (degrees, neutral `90`)
  * `TRIGGER`: `0` (unpressed) to `180` (fully pressed)
  * `DURATION`: Movement duration in ms (optional, default `200ms`)
* **Example:** `SERVO,90,50,90,90,0,100\n` (push left joystick forward)

### 3. Stepper Actuation (PC → ESP32)
*Valid in `MODE_RACING` when in `RUNNING` state.*
```text
STEPPER,LEFT,<rate_hz>\n     # Rotate steering wheel left continuously
STEPPER,RIGHT,<rate_hz>\n    # Rotate steering wheel right continuously
STEPPER,STOP\n               # Stop steering output immediately
```
* **Parameters:** `rate_hz` from `10` to `2000` (typical: `150`–`800` Hz).

### 4. Responses (ESP32 → PC)
```text
OK\n                       # Command executed successfully
ERR,<CODE>,<MESSAGE>\n     # Error response (e.g. ERR,201,Mode not in RUNNING state)
STATUS,<MODE>,<STATE>\n    # Status feedback (e.g. STATUS,RACING,RUNNING)
DEBUG,<MESSAGE>\n          # Firmware diagnostic message
```

---

## Installation & Getting Started

### Prerequisites
- **Operating System:** Windows 10/11, Linux, or macOS
- **Python:** Python 3.10+ (Python 3.12 recommended)
- **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (recommended for cross-project binary caching) or standard `pip`
- **Firmware IDE:** [PlatformIO](https://platformio.org/) (VS Code extension or CLI) for ESP32 flashing

### 1. Clone the Repository
```bash
git clone https://github.com/alfredjoejr/PathFinder.git
cd PathFinder
```

### 2. Set Up Virtual Environment & Dependencies

Using **`uv`** (instant, pre-cached wheels):
```powershell
# Create Python 3.12 virtual environment
uv venv --python 3.12

# Install dependencies from requirements.txt
uv pip install -r requirements.txt
```

*(Alternative)* Using standard Python `venv`:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Flash ESP32 Firmware
1. Open the [`ActuatorProgram/`](ActuatorProgram/) directory in VS Code with the **PlatformIO** extension installed.
2. Connect your ESP32 board via USB.
3. Build and upload:
   ```bash
   cd ActuatorProgram
   pio run -t upload
   ```

---

## How to Run

### Main Launcher Control Center
Run the main graphical control dashboard:
```powershell
uv run main.py
```
From the Control Center interface, you can launch:
- **VALORANT**: Autonomous lane navigation & servo aiming dashboard.
- **RACING**: Canny edge-density stepper steering auto-pilot.
- **TRACKMANIA (Auto)**: Multi-scanline road segmentation & PD steering auto-pilot.
- **PAC-MAN**:
  - **Manual Mode (Play)**: play the local Pygame version with `WASD` / arrow keys.
  - **Auto Mode ▾ → In-Computer Game**: launches the local game (`--auto`) together with the auto-pilot dashboard in screen-capture mode (`--capture-mode screen`).
  - **Auto Mode ▾ → External Computer**: launches the auto-pilot dashboard in camera mode (`--capture-mode camera`) for a game running on another PC.

### Direct Submodule Execution
You can also launch any dashboard or game directly:

```powershell
# Trackmania Auto-Pilot
uv run trackmania/trackmania_runner.py

# Racing Auto-Pilot
uv run racing/racing_runner.py

# Valorant Auto-Pilot
uv run mapper/valorant_runner.py

# Pac-Man (Manual Keyboard Play)
uv run pacman/pacman_game.py

# Pac-Man Auto-Pilot (camera / external computer)
uv run pacman/pacman_runner.py --capture-mode camera

# Pac-Man Auto-Pilot (screen capture of the local game)
uv run pacman/pacman_runner.py --capture-mode screen
```

### Running Automated Tests
```powershell
uv run python -m unittest discover tests -v
```

---

## Project Directory Structure

```text
PathFinder/
├── ActuatorProgram/               # ESP32 C++ firmware (PlatformIO)
│   ├── include/                   # Firmware headers (protocol, servo, stepper, mode)
│   ├── src/                       # Firmware source implementation
│   ├── platformio.ini             # PlatformIO ESP32 environment configuration
│   └── Screenshot 2026-06-24.png  # Physical hardware wiring schematic
│
├── mapper/                        # Valorant visual pipeline & A* pathfinder
│   ├── valorant_runner.py         # Autonomous Valorant GUI & CV dashboard
│   ├── mapRunner.py               # A* grid-based navigation
│   └── test.py                    # OpenCV trackbar tuner
│
├── racing/                        # Autonomous top-down car racing module
│   └── racing_runner.py           # Racing GUI with proportional stepper steering
│
├── trackmania/                    # Fully autonomous Trackmania module
│   └── trackmania_runner.py       # Road segmentation, PD steering & wheel control GUI
│
├── pacman/                        # Pac-Man arcade module
│   ├── pacman_game.py             # Pygame implementation with complete ghost AI
│   └── pacman_runner.py           # Auto-pilot dashboard with HSV tracking & servo mapper
│
├── tests/                         # Automated unit & stress test suites
│   ├── test_trackmania.py         # Trackmania vision & stepper integration tests
│   ├── test_launcher.py           # Launcher routing tests
│   └── test_ghost_ai.py           # Pac-Man ghost navigation tests
│
├── actuator_controller.py         # Thread-safe Python serial driver for ESP32
├── main.py                        # Central Tkinter game selection launcher
├── requirements.txt               # Python package dependencies
└── README.md                      # Project documentation
```

---

## Safety Features

1. **Firmware Watchdog Timeout**: If the PC stops sending commands for 30 seconds while in `RUNNING` state, the ESP32 automatically stops stepper pulses and moves all servos back to neutral (`90°`).
2. **State Gating**: Actuation commands (`SERVO` / `STEPPER`) are rejected unless the controller is in an active `RUNNING` mode state.
3. **Emergency Stop & Centering**: Closing any runner GUI or clicking `STOP AUTO-PILOT` sends immediate neutral commands, parks the steering wheel at its calibrated center, and resets the ESP32 state machine.
4. **Range Clamping**: All angles are strictly bounded between `0°` and `180°`, and stepper rates are clamped between `10` Hz and `2000` Hz.

---

## License

No license file has been added yet. All rights reserved by the repository owner unless stated otherwise.

