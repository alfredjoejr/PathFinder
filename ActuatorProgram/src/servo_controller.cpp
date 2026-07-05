#include "servo_controller.h"
#include "response_builder.h"

struct ServoState {
    uint8_t currentAngle;
    uint8_t targetAngle;
    uint16_t duration;
    unsigned long startTime;
    bool isMoving;
};

static ServoState servoStates[NUM_SERVOS];
static unsigned long updateStartTime = 0;

void ServoController::init() {
    ServoConfig::init();
    
    // Initialize all servo states
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
        const ServoCalibration* config = ServoConfig::getServoConfig(i);
        servoStates[i].currentAngle = config->neutralAngle;
        servoStates[i].targetAngle = config->neutralAngle;
        servoStates[i].duration = 0;
        servoStates[i].startTime = 0;
        servoStates[i].isMoving = false;
        
        // Set initial position
        setPWMDuty(i, angleToPWM(i, config->neutralAngle));
    }
    
    updateStartTime = millis();
}

bool ServoController::moveServo(uint8_t servoId, uint8_t targetAngle) {
    if (servoId >= NUM_SERVOS) return false;
    
    const ServoCalibration* config = ServoConfig::getServoConfig(servoId);
    if (!config) return false;
    
    // Validate angle range
    if (targetAngle < config->minAngle || targetAngle > config->maxAngle) {
        return false;
    }
    
    servoStates[servoId].currentAngle = targetAngle;
    servoStates[servoId].targetAngle = targetAngle;
    servoStates[servoId].isMoving = false;
    setPWMDuty(servoId, angleToPWM(servoId, targetAngle));
    
    return true;
}

bool ServoController::moveServoSmooth(uint8_t servoId, uint8_t targetAngle, uint16_t durationMs) {
    if (servoId >= NUM_SERVOS) return false;
    
    const ServoCalibration* config = ServoConfig::getServoConfig(servoId);
    if (!config) return false;
    
    // Validate angle range
    if (targetAngle < config->minAngle || targetAngle > config->maxAngle) {
        return false;
    }
    
    servoStates[servoId].targetAngle = targetAngle;
    servoStates[servoId].duration = durationMs;
    servoStates[servoId].startTime = millis();
    servoStates[servoId].isMoving = true;
    
    return true;
}

bool ServoController::moveAllServos(const BatchServoCommand& cmd) {
    // Validate all angles first
    if (cmd.lj_x > 180 || cmd.lj_y > 180 || cmd.rj_x > 180 || cmd.rj_y > 180 || cmd.trigger > 180) {
        return false;
    }
    
    // Start smooth movement for all servos
    moveServoSmooth(SERVO_LJ_X, cmd.lj_x, cmd.duration_ms);
    moveServoSmooth(SERVO_LJ_Y, cmd.lj_y, cmd.duration_ms);
    moveServoSmooth(SERVO_RJ_X, cmd.rj_x, cmd.duration_ms);
    moveServoSmooth(SERVO_RJ_Y, cmd.rj_y, cmd.duration_ms);
    moveServoSmooth(SERVO_TRIGGER, cmd.trigger, cmd.duration_ms);
    
    return true;
}

void ServoController::moveToNeutral() {
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
        const ServoCalibration* config = ServoConfig::getServoConfig(i);
        moveServo(i, config->neutralAngle);
    }
}

void ServoController::update() {
    unsigned long currentTime = millis();
    
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
        if (!servoStates[i].isMoving) continue;
        
        // Calculate interpolation progress
        unsigned long elapsedTime = currentTime - servoStates[i].startTime;
        
        if (elapsedTime >= servoStates[i].duration) {
            // Movement complete
            servoStates[i].currentAngle = servoStates[i].targetAngle;
            servoStates[i].isMoving = false;
        } else {
            // Interpolate position
            float progress = (float)elapsedTime / servoStates[i].duration;
            int8_t angleDiff = (int8_t)servoStates[i].targetAngle - (int8_t)servoStates[i].currentAngle;
            uint8_t newAngle = servoStates[i].currentAngle + (angleDiff * progress);
            servoStates[i].currentAngle = newAngle;
        }
        
        // Update PWM
        setPWMDuty(i, angleToPWM(i, servoStates[i].currentAngle));
    }
}

uint8_t ServoController::getCurrentPosition(uint8_t servoId) {
    if (servoId >= NUM_SERVOS) return 0;
    return servoStates[servoId].currentAngle;
}

uint8_t ServoController::getTargetPosition(uint8_t servoId) {
    if (servoId >= NUM_SERVOS) return 0;
    return servoStates[servoId].targetAngle;
}

bool ServoController::isMovementComplete() {
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
        if (servoStates[i].isMoving) {
            return false;
        }
    }
    return true;
}

void ServoController::setPWMDuty(uint8_t servoId, uint16_t pulseMicros) {
    if (servoId >= NUM_SERVOS) return;
    
    const ServoCalibration* config = ServoConfig::getServoConfig(servoId);
    if (!config) return;
    
    // Convert microseconds to PWM duty cycle for ESP32
    // Frequency is 50 Hz = 20ms period
    // Resolution is 16-bit (65535)
    // Duty = (pulse_micros / 20000) * 65535
    uint32_t duty = (pulseMicros * 65535) / 20000;
    ledcWrite(config->pwmChannel, duty);
}

uint16_t ServoController::angleToPWM(uint8_t servoId, uint8_t angle) {
    const ServoCalibration* config = ServoConfig::getServoConfig(servoId);
    if (!config) return SERVO_PWM_MID_US;
    
    // Linear interpolation: 0° -> minPulse, 180° -> maxPulse
    uint16_t pulse = config->minPulse + (angle * (config->maxPulse - config->minPulse)) / 180;
    return pulse;
}
