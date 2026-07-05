#include "mode_manager.h"
#include "response_builder.h"
#include "mode_handler.h"
#include "servo_controller.h"

// Static member initialization
ModeState ModeManager::currentState = STATE_IDLE;
GameMode ModeManager::currentMode = MODE_NONE;
unsigned long ModeManager::lastCommandTime = 0;

void ModeManager::init() {
    currentState = STATE_IDLE;
    currentMode = MODE_NONE;
    lastCommandTime = millis();
}

bool ModeManager::setMode(GameMode mode) {
    // Can only set mode if in IDLE or STOPPED state
    if (currentState == STATE_RUNNING) {
        return false;  // Cannot change mode while running
    }
    
    if (mode == MODE_NONE) {
        return false;  // Invalid mode
    }
    
    currentMode = mode;
    return transitionTo(STATE_MODE_SET);
}

bool ModeManager::startMode() {
    // Can only start if mode is set
    if (currentState != STATE_MODE_SET) {
        return false;
    }
    
    if (!transitionTo(STATE_RUNNING)) {
        return false;
    }

    lastCommandTime = millis();
    return true;
}

bool ModeManager::stopMode() {
    // Can stop from any active state
    if (currentState == STATE_IDLE) {
        return false;
    }

    if (!transitionTo(STATE_STOPPED)) {
        return false;
    }

    ModeHandler::onModeStop(currentMode);
    ServoController::moveToNeutral();
    return true;
}

bool ModeManager::resetToIdle() {
    if (currentState != STATE_STOPPED) {
        return false;
    }

    currentMode = MODE_NONE;
    return transitionTo(STATE_IDLE);
}

void ModeManager::checkTimeout() {
    // Only check timeout if mode is running
    if (currentState != STATE_RUNNING) {
        return;
    }
    
    unsigned long currentTime = millis();
    
    // Check if timeout has elapsed
    if (currentTime - lastCommandTime > COMMAND_TIMEOUT_MS) {
        // Timeout detected - stop mode and move servos to neutral
        stopMode();
    }
}

ModeState ModeManager::getState() {
    return currentState;
}

GameMode ModeManager::getMode() {
    return currentMode;
}

void ModeManager::updateCommandTime() {
    lastCommandTime = millis();
}

bool ModeManager::isServoCommandAllowed() {
    return (currentState == STATE_RUNNING);
}

bool ModeManager::isStepperCommandAllowed() {
    return (currentState == STATE_RUNNING && currentMode == MODE_RACING);
}

bool ModeManager::transitionTo(ModeState newState) {
    // Validate state transition
    switch (currentState) {
        case STATE_IDLE:
            if (newState != STATE_MODE_SET) return false;
            break;
        case STATE_MODE_SET:
            if (newState != STATE_RUNNING && newState != STATE_IDLE) return false;
            break;
        case STATE_RUNNING:
            if (newState != STATE_STOPPED) return false;
            break;
        case STATE_STOPPED:
            if (newState != STATE_IDLE) return false;
            break;
        default:
            return false;
    }
    
    currentState = newState;
    return true;
}
