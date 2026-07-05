#ifndef SERVO_CONTROLLER_H
#define SERVO_CONTROLLER_H

#include <Arduino.h>
#include "protocol.h"
#include "servo_config.h"

class ServoController {
public:
    // Initialize servo PWM control
    static void init();
    
    // Move a single servo to a target angle (instant)
    static bool moveServo(uint8_t servoId, uint8_t targetAngle);
    
    // Move a single servo with interpolation
    static bool moveServoSmooth(uint8_t servoId, uint8_t targetAngle, uint16_t durationMs);
    
    // Move all servos with interpolation (batch command)
    static bool moveAllServos(const BatchServoCommand& cmd);
    
    // Move all servos to neutral position
    static void moveToNeutral();
    
    // Update servo positions (call this in main loop for smooth movement)
    static void update();
    
    // Get current servo position
    static uint8_t getCurrentPosition(uint8_t servoId);
    
    // Get target servo position
    static uint8_t getTargetPosition(uint8_t servoId);
    
    // Check if all servos have reached their targets
    static bool isMovementComplete();
    
private:
    // Internal: Set PWM duty for a servo
    static void setPWMDuty(uint8_t servoId, uint16_t pulseMicros);
    
    // Internal: Convert angle to PWM pulse width
    static uint16_t angleToPWM(uint8_t servoId, uint8_t angle);
    
    // Internal: Interpolate between current and target positions
    static void interpolatePositions();
};

#endif
