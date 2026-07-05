#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <Arduino.h>

// ==================== COMMAND TYPES ====================
enum CommandType {
    CMD_MODE,    // MODE commands
    CMD_SERVO,   // SERVO commands
    CMD_STEPPER, // STEPPER commands
    CMD_UNKNOWN
};

// ==================== MODE STATES ====================
enum ModeState {
    STATE_IDLE,      // Waiting for mode selection
    STATE_MODE_SET,  // Mode selected, ready to start
    STATE_RUNNING,   // Game mode active, accepting servo commands
    STATE_STOPPED    // Game stopped, servos at neutral
};

enum GameMode {
    MODE_VALORANT,
    MODE_RACING,
    MODE_NONE
};

enum ModeCommand {
    MODE_CMD_SET,     // MODE,SET,<mode_name>
    MODE_CMD_START,   // MODE,START
    MODE_CMD_STOP,    // MODE,STOP
    MODE_CMD_RESET,   // MODE,RESET
    MODE_CMD_STATUS,  // MODE,STATUS
    MODE_CMD_UNKNOWN
};

// ==================== ERROR CODES ====================
// 1xx: Mode errors
#define ERR_MODE_INVALID_MODE         100
#define ERR_MODE_CANNOT_CHANGE_RUNNING 101
#define ERR_MODE_INVALID_TRANSITION    102

// 2xx: Servo errors
#define ERR_SERVO_OUT_OF_RANGE        200
#define ERR_SERVO_MODE_NOT_RUNNING    201
#define ERR_SERVO_INCOMPLETE_COMMAND  202
#define ERR_SERVO_INVALID_DURATION    203

// 2xx: Stepper errors
#define ERR_STEPPER_MODE_NOT_RUNNING  204
#define ERR_STEPPER_INVALID_DIRECTION 205
#define ERR_STEPPER_INVALID_SPEED     206

// 3xx: Communication errors
#define ERR_COMM_MALFORMED_COMMAND    300
#define ERR_COMM_UNKNOWN_COMMAND      301
#define ERR_COMM_BUFFER_OVERFLOW      302

// ==================== SERVO CONFIGURATION ====================
#define NUM_SERVOS                    5
#define SERVO_MIN_ANGLE               0
#define SERVO_MAX_ANGLE               180
#define SERVO_NEUTRAL_ANGLE           90

#define SERVO_LJ_X                    0  // Left Joystick X
#define SERVO_LJ_Y                    1  // Left Joystick Y
#define SERVO_RJ_X                    2  // Right Joystick X
#define SERVO_RJ_Y                    3  // Right Joystick Y
#define SERVO_TRIGGER                 4  // Trigger Button

// ==================== MOVEMENT PARAMETERS ====================
#define DEFAULT_MOVEMENT_DURATION_MS  200  // Default smooth movement time
#define MIN_MOVEMENT_DURATION_MS      50   // Minimum movement time
#define MAX_MOVEMENT_DURATION_MS      2000 // Maximum movement time

// ==================== TIMEOUT & COMMUNICATION ====================
#define SERIAL_BAUD_RATE              115200
#define COMMAND_TIMEOUT_MS            30000  // 30 seconds
#define SERIAL_BUFFER_SIZE            256
#define COMMAND_TERMINATOR            '\n'

// ==================== STEPPER CONFIGURATION ====================
#define STEPPER_STEP_PIN              4
#define STEPPER_DIR_PIN               2
#define DEFAULT_STEPPER_RATE_HZ       400
#define MIN_STEPPER_RATE_HZ           10
#define MAX_STEPPER_RATE_HZ           2000

// ==================== STRUCT DEFINITIONS ====================
struct ServoCommand {
    uint8_t servo_id;      // Which servo (SERVO_LJ_X, etc.)
    uint8_t position;      // Target angle (0-180)
    uint16_t duration_ms;  // Movement time in milliseconds
};

struct BatchServoCommand {
    uint8_t lj_x;          // Left Joystick X (0-180)
    uint8_t lj_y;          // Left Joystick Y (0-180)
    uint8_t rj_x;          // Right Joystick X (0-180)
    uint8_t rj_y;          // Right Joystick Y (0-180)
    uint8_t trigger;       // Trigger Button (0-180)
    uint16_t duration_ms;  // Movement time in milliseconds
};

enum StepperDirection {
    STEPPER_DIR_STOP = 0,
    STEPPER_DIR_LEFT,
    STEPPER_DIR_RIGHT
};

struct StepperCommand {
    StepperDirection direction;
    uint16_t rate_hz;
};

#endif
