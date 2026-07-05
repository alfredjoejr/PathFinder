# Game Playing Robot - Valorant Controller Firmware

## Overview

ESP32-based firmware for controlling game inputs through serial commands from a PC-based game logic program. It currently supports Valorant servo control and racing-mode stepper steering, with smooth interpolation for servos and non-blocking pulse generation for the stepper.

## Architecture

### System Components

```
PC Game Logic + GUI
    ↓ (Serial/USB)
ESP32 Firmware
  ├─ Serial Input Handler (parse MODE, SERVO, and STEPPER commands)
    ├─ Mode Manager (state machine)
    ├─ Servo Controller (PWM + smooth movement)
  ├─ Racing Stepper Controller (DIR + STEP pulses)
    ├─ Mode Handler (mode-specific logic)
    └─ Response Builder (feedback to PC)
    ↓ (PWM signals)
5 Servo Motors
```

### State Machine

```
IDLE
  ↓
MODE_SET (game mode selected by GUI)
  ↓
RUNNING (mode active, receiving servo commands)
  ↓
STOPPED (game stopped, servos at neutral)
  ↓
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
MODE,STOP\n             # Stop the game (return to neutral)
MODE,RESET\n           # Return to IDLE so another game mode can be selected
MODE,STATUS\n           # Request current status
```

#### 2. Servo Commands (PC → ESP32)

Send servo positions during gameplay (only in RUNNING state):

```
SERVO,LJX,LJY,RJX,RJY,TRIGGER[,DURATION]\n

Parameters:
  LJX:       Left Joystick X angle (0-180°)
  LJY:       Left Joystick Y angle (0-180°)
  RJX:       Right Joystick X angle (0-180°)
  RJY:       Right Joystick Y angle (0-180°)
  TRIGGER:   Trigger button angle (0=unpressed, 180=pressed)
  DURATION:  Movement time in ms (optional, default 200ms)

Example:
  SERVO,90,90,90,90,0,200\n     # Center all, trigger unpressed, move over 200ms
```

#### 3. Stepper Commands (PC → ESP32)

Use these in racing mode to rotate the steering wheel until you stop it:

```
STEPPER,LEFT[,RATE_HZ]\n      # Rotate steering wheel left continuously
STEPPER,RIGHT[,RATE_HZ]\n     # Rotate steering wheel right continuously
STEPPER,STOP\n               # Stop stepper output immediately
```

Examples:

```
STEPPER,LEFT,400\n
STEPPER,RIGHT,600\n
STEPPER,STOP\n
```

### Response Messages (ESP32 → PC)

```
OK\n                              # Command executed successfully
ERR,<CODE>,<MESSAGE>\n            # Error with code and description
STATUS,<MODE>,<STATE>\n           # Status response
DEBUG,<MESSAGE>\n                 # Debug information (optional)
```

**Error Codes:**

- `100`: Invalid mode name
- `101`: Cannot change mode while running
- `102`: Invalid state transition
- `200`: Servo position out of range (0-180)
- `201`: SERVO command sent but mode not RUNNING
- `202`: Incomplete servo command
- `203`: Invalid duration parameter
- `204`: Stepper command sent but mode not RUNNING in RACING
- `205`: Reserved for future stepper direction validation
- `206`: Reserved for future stepper speed validation
- `300`: Malformed command
- `301`: Unknown command type
- `302`: Serial buffer overflow

### Example Communication Sequence

```
[Startup]
→ MODE,SET,VALORANT\n
← STATUS,VALORANT,MODE_SET\n

[Start Game]
→ MODE,START\n
← STATUS,VALORANT,RUNNING\n

[During Gameplay - repeated every 50ms]
→ SERVO,90,95,85,100,50,100\n
← OK\n

[Stop Game]
→ MODE,STOP\n
← STATUS,VALORANT,STOPPED\n

[Reset to IDLE]
→ MODE,RESET\n
← STATUS,NONE,IDLE\n

[Switch to Other Game]
→ MODE,SET,RACING\n
← STATUS,RACING,MODE_SET\n
→ MODE,START\n
← STATUS,RACING,RUNNING\n

[Race Steering]
→ STEPPER,LEFT,400\n
← OK\n
→ STEPPER,STOP\n
← OK\n
```

## Servo Configuration

### Servo Mapping

| Servo ID | GPIO Pin | Purpose          | Neutral |
| -------- | -------- | ---------------- | ------- |
| 0        | GPIO 25  | Left Joystick X  | 90°     |
| 1        | GPIO 26  | Left Joystick Y  | 90°     |
| 2        | GPIO 27  | Right Joystick X | 90°     |
| 3        | GPIO 32  | Right Joystick Y | 90°     |
| 4        | GPIO 33  | Trigger Button   | 0°      |

### PWM Settings

- **Frequency**: 50 Hz (standard servo frequency)
- **Resolution**: 16-bit
- **Pulse Range**: 1000-2000 µs (0-180°)
- **Baud Rate**: 115200

## File Structure

```
src/
├── main.cpp                    # Main firmware loop & command routing
├── response_builder.cpp        # Serial response messages
├── serial_handler.cpp          # Command parsing
├── mode_manager.cpp            # State machine logic
├── mode_handler.cpp            # Mode-specific callbacks
├── servo_controller.cpp        # PWM & servo control
├── racing_stepper.cpp          # Stepper steering control
└── servo_config.cpp            # Servo calibration data

include/
├── protocol.h                  # Protocol definitions & enums
├── response_builder.h          # Response message interface
├── serial_handler.h            # Command parsing interface
├── mode_manager.h              # State machine interface
├── mode_handler.h              # Mode handler interface
├── servo_controller.h          # Servo control interface
├── servo_config.h              # Servo configuration
├── mode_config.h               # Mode configurations
├── racing_stepper.h            # Racing stepper interface
└── racing_paddle.h             # [STUB] Racing mode paddles
```

## Key Features

✅ **Modular Design**: Clean separation of concerns  
✅ **Smooth Interpolation**: Configurable movement duration  
✅ **State Protection**: SERVO commands only in RUNNING state  
✅ **Racing Mode Support**: Stepper steering with START/STOP/RESET flow  
✅ **Timeout Detection**: Automatic neutral on 5s inactivity  
✅ **Error Feedback**: Detailed error codes to PC  
✅ **Reset Flow**: MODE,RESET returns to IDLE so the GUI can switch games  
✅ **Non-blocking**: Uses timer-based interpolation

## Safety Features

1. **Failsafe**: On error, servos hold last valid position
2. **Timeout**: If no command for 5 seconds while RUNNING, move to neutral
3. **Range Validation**: All servo positions validated (0-180°)
4. **State Gating**: SERVO commands rejected unless mode RUNNING
5. **Neutral Fallback**: MODE,STOP moves all servos to neutral
6. **Game Switch Reset**: MODE,RESET returns the controller to IDLE so the GUI can select another mode
7. **Stepper Gating**: STEPPER commands are only accepted in `MODE_RACING` while RUNNING

## Testing Checklist

- [ ] Serial communication at 115200 baud
- [ ] MODE,SET,VALORANT → returns correct STATUS
- [ ] MODE,START → transitions to RUNNING
- [ ] SERVO commands → servos move smoothly
- [ ] Duration parameter → servos move over specified time
- [ ] MODE,STOP → servos return to neutral
- [ ] MODE,RESET → returns to IDLE
- [ ] SERVO command in non-RUNNING state → ERR,201
- [ ] MODE,SET,RACING → returns correct STATUS
- [ ] STEPPER,LEFT / STEPPER,RIGHT → rotates steering wheel
- [ ] STEPPER,STOP → stops motor immediately
- [ ] Invalid angle (>180) → ERR,200
- [ ] Timeout after 5s inactivity → auto-neutral

## PC Test Code

Use this quick Python script to test the serial protocol from your PC.

### Requirements

- Python 3
- `pyserial` installed: `pip install pyserial`
- ESP32 connected on the same COM port used by the script

If you do not have Python installed, you can still test the same command flow from the VS Code serial monitor or any terminal program that can send newline-terminated text.

### Example Script

```python
import time
import serial

PORT = "COM5"  # Change to your ESP32 port
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
  time.sleep(2)

  def send(cmd):
    print(f"> {cmd}")
    ser.write((cmd + "\n").encode())
    response = ser.readline().decode(errors="ignore").strip()
    if response:
      print(f"< {response}")

  send("MODE,SET,RACING")
  send("MODE,START")
  time.sleep(1)
  send("STEPPER,LEFT,400")
  time.sleep(2)
  send("STEPPER,STOP")
  send("MODE,STOP")
  send("MODE,RESET")
  send("MODE,SET,VALORANT")
  send("MODE,START")
```

### Test Sequence

1. Open the serial port at 115200 baud.
2. Send `MODE,SET,RACING` and confirm `STATUS,RACING,MODE_SET`.
3. Send `MODE,START` and confirm `STATUS,RACING,RUNNING`.
4. Send `STEPPER,LEFT,400` and verify the stepper turns left.
5. Send `STEPPER,STOP` and verify the stepper stops.
6. Send `MODE,STOP` then `MODE,RESET`.
7. Select the next mode with `MODE,SET,VALORANT` or `MODE,SET,RACING`.

## Future Extensions

### Racing Mode (Ready to implement)

- [x] Stepper motor control for steering wheel
- [ ] 2 paddle servo motors for gas/brake
- [x] MODE,SET,RACING support
- [x] MODE,RESET support
- [ ] Merge with VALORANT mode in mode manager

### Additional Features

- [ ] EEPROM calibration storage
- [ ] Per-servo speed limiting
- [ ] Acceleration profiles
- [ ] LED status indicators
- [ ] WiFi support (as alternative to Serial)

## Calibration Notes

If servos need tuning, adjust `servo_config.cpp`:

```cpp
// Example: Adjust neutral position for left joystick X
ServoCalibration servoConfigs[NUM_SERVOS] = {
    {SERVO_LJ_X, SERVO_LJ_X_PIN, 0, 0, 180, 85, SERVO_PWM_MIN_US, SERVO_PWM_MAX_US},  // Changed 90 → 85
    // ...
};
```

## Dependencies

- Arduino Framework (via PlatformIO)
- ESP32 SDK (espressif32 platform)
- None (standard libraries only)

## Build & Upload

```bash
# Build
pio run

# Upload to ESP32
pio run -t upload

# Monitor serial output
pio device monitor --baud 115200
```

## Troubleshooting

**Q: Servos not moving?**

- Check GPIO pin connections
- Verify PWM frequency (should be 50 Hz)
- Test with `MODE,SET,VALORANT` → `MODE,START` → `SERVO,90,90,90,90,0,200`

**Q: Servo movements jerky?**

- Increase duration parameter in SERVO command
- Check servo power supply (may be insufficient)

**Q: Timeout moving servos to neutral unexpectedly?**

- Ensure PC sends commands within 5 seconds in RUNNING state
- Adjust COMMAND_TIMEOUT_MS in protocol.h if needed

**Q: Serial communication errors?**

- Verify baud rate is 115200
- Check USB cable connection
- Reset ESP32 if needed
