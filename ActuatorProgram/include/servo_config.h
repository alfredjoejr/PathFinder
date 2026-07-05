#ifndef SERVO_CONFIG_H
#define SERVO_CONFIG_H

#include <Arduino.h>
#include "protocol.h"

// ==================== GPIO PIN CONFIGURATION ====================
// Servo GPIO pin assignments for ESP32
#define SERVO_LJ_X_PIN    25  // Left Joystick X
#define SERVO_LJ_Y_PIN    26  // Left Joystick Y
#define SERVO_RJ_X_PIN    27  // Right Joystick X
#define SERVO_RJ_Y_PIN    32  // Right Joystick Y
#define SERVO_TRIGGER_PIN 33  // Trigger Button

// ==================== PWM CONFIGURATION ====================
#define PWM_FREQUENCY     50    // 50 Hz (standard servo frequency)
#define PWM_RESOLUTION    16    // 16-bit resolution for ESP32
#define PWM_CHANNEL_BASE  0     // Starting PWM channel

// Servo pulse width range (in microseconds)
// Standard servo: 1000 µs = 0°, 2000 µs = 180°
#define SERVO_PWM_MIN_US  1000
#define SERVO_PWM_MAX_US  2000
#define SERVO_PWM_MID_US  1500

// ==================== SERVO CALIBRATION ====================
struct ServoCalibration {
    uint8_t servoId;
    uint8_t pin;
    uint8_t pwmChannel;
    uint8_t minAngle;      // Physical minimum angle
    uint8_t maxAngle;      // Physical maximum angle
    uint8_t neutralAngle;  // Default neutral position
    uint16_t minPulse;     // PWM pulse for 0 degrees
    uint16_t maxPulse;     // PWM pulse for 180 degrees
};

class ServoConfig {
public:
    // Initialize servo configuration
    static void init();
    
    // Get servo calibration by ID
    static const ServoCalibration* getServoConfig(uint8_t servoId);
    
    // Get all servo configurations
    static const ServoCalibration* getAllConfigs();
    
    // Get number of servos
    static uint8_t getServoCount();
    
private:
    // Servo calibration data for 5 servos
    static ServoCalibration servoConfigs[NUM_SERVOS];
};

#endif
