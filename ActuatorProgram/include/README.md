# Game Playing Robot - Actuator Firmware

## Overview

ESP32-based firmware for controlling game inputs through serial commands from a PC-based game logic program. It supports Valorant dual-stick servo control and racing-mode steering (stepper) with paddle servos (gas/brake), with smooth interpolation for servos, non-blocking pulse generation, travel limits for the stepper, and combined `RACE` packet execution.

## Architecture

### System Components

```
PC Game Logic + GUI
    ↓ (Serial/USB 115200 baud)
ESP32 Firmware
    ├─ Serial Input Handler (parse MODE, SERVO, RACE, and STEPPER commands)
    ├─ Mode Manager (state machine)
    ├─ Servo Controller (PWM + smooth movement for 7 servos)
    ├─ Racing Stepper Controller (DIR + STEP pulses + travel limit)
    ├─ Mode Handler (mode-specific logic)
    └─ Response Builder (feedback to PC)
    ↓ (PWM & STEP/DIR signals)
7 Servo Motors + 1 Stepper Driver
```

### State Machine

```
IDLE
  ↓ MODE,SET,VALORANT or MODE,SET,RACING
MODE_SET (game mode selected by GUI)
  ↓ MODE,START
RUNNING (mode active, receiving gameplay commands)
  ↓ MODE,STOP (or 30s timeout)
STOPPED (game stopped, all 7 servos at neutral, stepper stopped)
  ↓ MODE,RESET
IDLE
```

## Communication Protocol

### Command Types

#### 1. Mode Commands (PC → ESP32)

Control game mode from GUI:

```
MODE,SET,VALORANT\n     # Set game to VALORANT mode
MODE,SET,RACING\n       # Set game to RACING mode
MODE,START\n            # Start the game (transition to RUNNING)
MODE,STOP\n             # Stop the game (return all 7 servos to neutral, stop stepper)
MODE,RESET\n           # Return to IDLE so another game mode can be selected
MODE,STATUS\n           # Request current status
```

#### 2. Servo Commands (Valorant Mode)

Send servo positions during gameplay (only in RUNNING state):

```
SERVO,LJX,LJY,RJX,RJY,TRIGGER[,DURATION]\n

Parameters:
  LJX:       Left Joystick X angle (0-180°, neutral 90)
  LJY:       Left Joystick Y angle (0-180°, neutral 90)
  RJX:       Right Joystick X angle (0-180°, neutral 90)
  RJY:       Right Joystick Y angle (0-180°, neutral 90)
  TRIGGER:   Trigger button angle (0=unpressed, 180=pressed, neutral 0)
  DURATION:  Movement time in ms (optional, default 200ms)

Example:
  SERVO,90,90,90,90,0,200\n     # Center all, trigger unpressed, move over 200ms
```

#### 3. Race Commands (Racing Mode - Preferred)

Combined steering and paddle commands for Trackmania / racing:

```
RACE,LEFT,<RATE_HZ>,<LEFT_PADDLE>,<RIGHT_PADDLE>\n
RACE,RIGHT,<RATE_HZ>,<LEFT_PADDLE>,<RIGHT_PADDLE>\n
RACE,STOP\n

Parameters:
  Direction:     LEFT or RIGHT
  RATE_HZ:       10-2000 step pulses/sec
  LEFT_PADDLE:   0-180° (neutral 90, brake toward 180)
  RIGHT_PADDLE:  0-180° (neutral 90, gas toward 180)

Examples:
  RACE,LEFT,800,90,180\n     # Steer left at 800 Hz, full gas (right paddle 180), no brake
  RACE,RIGHT,400,180,90\n    # Steer right at 400 Hz, full brake (left paddle 180), no gas
  RACE,STOP\n                # Halts stepper and resets both paddles to 90° neutral
```

#### 4. Stepper Commands (Racing Mode - Legacy / Fine Control)

```
STEPPER,LEFT[,RATE_HZ]\n      # Rotate steering wheel left continuously
STEPPER,RIGHT[,RATE_HZ]\n     # Rotate steering wheel right continuously
STEPPER,STOP\n               # Stop stepper output without modifying paddle angles
```

### Response Messages (ESP32 → PC)

```
OK\n                              # Command executed successfully
ERR,<CODE>,<MESSAGE>\n            # Error with code and description
STATUS,<MODE>,<STATE>\n           # Status response (e.g. STATUS,RACING,RUNNING)
DEBUG,<MESSAGE>\n                 # Debug information (e.g. boot message)
```

**Error Codes:**

- `100`: Invalid mode name
- `101`: Cannot change mode while running
- `102`: Invalid state transition
- `200`: Servo position out of range (0-180)
- `201`: SERVO command sent but mode not RUNNING
- `202`: Incomplete servo command
- `203`: Invalid duration parameter
- `204`: Racing command (RACE or STEPPER) sent but mode not RUNNING in RACING
- `205`: Reserved for future stepper direction validation
- `206`: Reserved for future stepper speed validation
- `300`: Malformed command
- `301`: Unknown command type
- `302`: Serial buffer overflow

## Hardware Configuration

### Servos (PWM 50 Hz, 1000–2000 µs for 0–180°)

| Servo ID | GPIO Pin | Channel | Purpose                 | Neutral | Mode     |
| -------- | -------- | ------- | ----------------------- | ------- | -------- |
| 0        | GPIO 25  | 0       | Left Joystick X         | 90°     | Valorant |
| 1        | GPIO 26  | 1       | Left Joystick Y         | 90°     | Valorant |
| 2        | GPIO 27  | 2       | Right Joystick X        | 90°     | Valorant |
| 3        | GPIO 32  | 3       | Right Joystick Y        | 90°     | Valorant |
| 4        | GPIO 33  | 4       | Trigger Button          | 0°      | Valorant |
| 5        | GPIO 13  | 5       | Left Paddle (Brake)     | 90°     | Racing   |
| 6        | GPIO 14  | 6       | Right Paddle (Throttle) | 90°     | Racing   |

### Stepper Motor

| Signal | GPIO Pin | Description |
| ------ | -------- | ----------- |
| STEP   | GPIO 4   | Step pulse (5 µs high) |
| DIR    | GPIO 16  | Direction (LOW = LEFT, HIGH = RIGHT) |

Software travel limit is `STEPPER_MAX_POSITION_STEPS` (~500 steps) in each direction.

## Safety Features

1. **Failsafe**: On error, actuators maintain last valid position.
2. **Watchdog Timeout**: Inactivity for 30 seconds while `RUNNING` transitions to `STOPPED` (all 7 servos to neutral, stepper stopped).
3. **Travel Limits**: Stepper stops pulsing beyond ±500 steps.
4. **State Gating**: `SERVO` commands require `RUNNING`; `RACE` commands require `RACING` + `RUNNING`.
5. **Mode Isolation**: Switching between Valorant and Racing requires `MODE,STOP` then `MODE,RESET`.
