#include <Arduino.h>
#include <string.h>
#include "protocol.h"
#include "response_builder.h"
#include "serial_handler.h"
#include "mode_manager.h"
#include "mode_handler.h"
#include "servo_controller.h"
#include "servo_config.h"
#include "racing_stepper.h"

// ==================== GLOBALS ====================
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 100;  // 100ms

// ==================== FORWARD DECLARATIONS ====================
void processCommand();
void processModeCommand(const char* cmdBuffer);
void processServoCommand(const char* cmdBuffer);
void processStepperCommand(const char* cmdBuffer);
void sendPeriodicStatus();

// ==================== SETUP ====================
void setup() {
    // Initialize communication
    ResponseBuilder::init(SERIAL_BAUD_RATE);
    SerialHandler::init(SERIAL_BAUD_RATE);
    
    // Initialize mode manager
    ModeManager::init();
    
    // Initialize servo controller
    ServoController::init();

    // Initialize racing stepper controller
    RacingStepper::init();
    
    delay(500);
    
    // Send startup message
    ResponseBuilder::sendDebug("System initialized");
    ResponseBuilder::sendStatus(MODE_NONE, STATE_IDLE);
}

// ==================== MAIN LOOP ====================
void loop() {
    // Update servo positions (smooth movement interpolation)
    ServoController::update();

    // Update racing stepper pulses
    RacingStepper::update();
    
    // Check for mode timeout
    ModeManager::checkTimeout();
    
    // Check for incoming serial commands
    SerialHandler::update();
    
    // If a complete command was received, process it
    if (SerialHandler::hasCommand()) {
        processCommand();
        SerialHandler::clearBuffer();
    }
    
    // Optional: Send periodic status updates (for monitoring)
    sendPeriodicStatus();
    
    delay(10);  // Small delay to prevent overwhelming the loop
}

// ==================== COMMAND PROCESSING ====================
void processCommand() {
    const char* cmdBuffer = SerialHandler::getBuffer();
    if (!cmdBuffer || cmdBuffer[0] == '\0') {
        return;
    }
    
    CommandType cmdType = SerialHandler::getCommandType(cmdBuffer);
    
    if (cmdType == CMD_MODE) {
        processModeCommand(cmdBuffer);
    } else if (cmdType == CMD_SERVO) {
        processServoCommand(cmdBuffer);
    } else if (cmdType == CMD_STEPPER) {
        processStepperCommand(cmdBuffer);
    } else {
        ResponseBuilder::sendError(ERR_COMM_UNKNOWN_COMMAND, "Unknown command type");
    }
}

void processModeCommand(const char* cmdBuffer) {
    ModeCommand modeCmd;
    GameMode mode;
    
    // Cast away const for parsing (parser uses strtok which modifies)
    char tempBuffer[SERIAL_BUFFER_SIZE];
    strncpy(tempBuffer, cmdBuffer, SERIAL_BUFFER_SIZE - 1);
    tempBuffer[SERIAL_BUFFER_SIZE - 1] = '\0';
    
    if (!SerialHandler::parseModeCommand(tempBuffer, modeCmd, mode)) {
        ResponseBuilder::sendError(ERR_COMM_MALFORMED_COMMAND, "Invalid MODE command format");
        return;
    }
    
    switch (modeCmd) {
        case MODE_CMD_SET:
            if (!ModeManager::setMode(mode)) {
                if (ModeManager::getState() == STATE_RUNNING) {
                    ResponseBuilder::sendError(ERR_MODE_CANNOT_CHANGE_RUNNING, "Cannot change mode while running");
                } else {
                    ResponseBuilder::sendError(ERR_MODE_INVALID_TRANSITION, "Invalid mode transition");
                }
                return;
            }
            ResponseBuilder::sendStatus(ModeManager::getMode(), ModeManager::getState());
            break;
            
        case MODE_CMD_START:
            if (!ModeManager::startMode()) {
                ResponseBuilder::sendError(ERR_MODE_INVALID_TRANSITION, "Invalid mode transition");
                return;
            }
            ModeHandler::onModeStart(ModeManager::getMode());
            ResponseBuilder::sendStatus(ModeManager::getMode(), ModeManager::getState());
            break;
            
        case MODE_CMD_STOP:
            if (!ModeManager::stopMode()) {
                ResponseBuilder::sendError(ERR_MODE_INVALID_TRANSITION, "Cannot stop in current state");
                return;
            }
            ResponseBuilder::sendStatus(ModeManager::getMode(), ModeManager::getState());
            break;

        case MODE_CMD_RESET:
            if (!ModeManager::resetToIdle()) {
                ResponseBuilder::sendError(ERR_MODE_INVALID_TRANSITION, "Can only reset from STOPPED state");
                return;
            }
            ResponseBuilder::sendStatus(ModeManager::getMode(), ModeManager::getState());
            break;
            
        case MODE_CMD_STATUS:
            ResponseBuilder::sendStatus(ModeManager::getMode(), ModeManager::getState());
            break;
            
        default:
            ResponseBuilder::sendError(ERR_COMM_UNKNOWN_COMMAND, "Unknown MODE command");
    }
}

void processServoCommand(const char* cmdBuffer) {
    // Check if mode is running
    if (!ModeManager::isServoCommandAllowed()) {
        ResponseBuilder::sendError(ERR_SERVO_MODE_NOT_RUNNING, "Mode not in RUNNING state");
        return;
    }
    
    BatchServoCommand servoCmd;
    
    // Cast away const for parsing
    char tempBuffer[SERIAL_BUFFER_SIZE];
    strncpy(tempBuffer, cmdBuffer, SERIAL_BUFFER_SIZE - 1);
    tempBuffer[SERIAL_BUFFER_SIZE - 1] = '\0';
    
    if (!SerialHandler::parseServoCommand(tempBuffer, servoCmd)) {
        ResponseBuilder::sendError(ERR_SERVO_INCOMPLETE_COMMAND, "Invalid SERVO command format");
        return;
    }
    
    // Execute the servo command
    if (!ServoController::moveAllServos(servoCmd)) {
        ResponseBuilder::sendError(ERR_SERVO_OUT_OF_RANGE, "Servo position out of range");
        return;
    }
    
    // Update command time for timeout tracking
    ModeManager::updateCommandTime();
    
    // Send confirmation
    ResponseBuilder::sendOK();
}

void processStepperCommand(const char* cmdBuffer) {
    StepperCommand stepperCmd;

    char tempBuffer[SERIAL_BUFFER_SIZE];
    strncpy(tempBuffer, cmdBuffer, SERIAL_BUFFER_SIZE - 1);
    tempBuffer[SERIAL_BUFFER_SIZE - 1] = '\0';

    if (!SerialHandler::parseStepperCommand(tempBuffer, stepperCmd)) {
        ResponseBuilder::sendError(ERR_COMM_MALFORMED_COMMAND, "Invalid STEPPER command format");
        return;
    }

    if (stepperCmd.direction == STEPPER_DIR_STOP) {
        RacingStepper::stop();
        ResponseBuilder::sendOK();
        return;
    }

    if (!ModeManager::isStepperCommandAllowed()) {
        ResponseBuilder::sendError(ERR_STEPPER_MODE_NOT_RUNNING, "Racing stepper not allowed in current state");
        return;
    }

    RacingStepper::start(stepperCmd.direction, stepperCmd.rate_hz);
    ModeManager::updateCommandTime();
    ResponseBuilder::sendOK();
}

void sendPeriodicStatus() {
    unsigned long currentTime = millis();
    
    if (currentTime - lastStatusUpdate >= STATUS_UPDATE_INTERVAL) {
        // Uncomment below to send periodic status updates
        // ResponseBuilder::sendStatus(ModeManager::getMode(), ModeManager::getState());
        lastStatusUpdate = currentTime;
    }
}