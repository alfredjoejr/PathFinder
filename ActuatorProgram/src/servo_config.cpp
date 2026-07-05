#include "servo_config.h"

// Static servo configuration data
ServoCalibration ServoConfig::servoConfigs[NUM_SERVOS] = {
    // Left Joystick X
    {SERVO_LJ_X, SERVO_LJ_X_PIN, 0, 0, 180, 90, SERVO_PWM_MIN_US, SERVO_PWM_MAX_US},
    // Left Joystick Y
    {SERVO_LJ_Y, SERVO_LJ_Y_PIN, 1, 0, 180, 90, SERVO_PWM_MIN_US, SERVO_PWM_MAX_US},
    // Right Joystick X
    {SERVO_RJ_X, SERVO_RJ_X_PIN, 2, 0, 180, 90, SERVO_PWM_MIN_US, SERVO_PWM_MAX_US},
    // Right Joystick Y
    {SERVO_RJ_Y, SERVO_RJ_Y_PIN, 3, 0, 180, 90, SERVO_PWM_MIN_US, SERVO_PWM_MAX_US},
    // Trigger Button
    {SERVO_TRIGGER, SERVO_TRIGGER_PIN, 4, 0, 180, 0, SERVO_PWM_MIN_US, SERVO_PWM_MAX_US}
};

void ServoConfig::init() {
    // Initialize all PWM channels
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
        ledcSetup(servoConfigs[i].pwmChannel, PWM_FREQUENCY, PWM_RESOLUTION);
        ledcAttachPin(servoConfigs[i].pin, servoConfigs[i].pwmChannel);
    }
}

const ServoCalibration* ServoConfig::getServoConfig(uint8_t servoId) {
    if (servoId >= NUM_SERVOS) {
        return NULL;
    }
    return &servoConfigs[servoId];
}

const ServoCalibration* ServoConfig::getAllConfigs() {
    return servoConfigs;
}

uint8_t ServoConfig::getServoCount() {
    return NUM_SERVOS;
}
