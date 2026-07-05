#include "serial_handler.h"
#include <string.h>

// Static member initialization
char SerialHandler::buffer[SERIAL_BUFFER_SIZE];
size_t SerialHandler::bufferIndex = 0;

void SerialHandler::init(uint32_t baudRate) {
    Serial.begin(baudRate);
    delay(100);
    bufferIndex = 0;
    memset(buffer, 0, SERIAL_BUFFER_SIZE);
}

void SerialHandler::update() {
    while (Serial.available() > 0) {
        char c = Serial.read();
        
        if (c == COMMAND_TERMINATOR) {
            // Command complete
            buffer[bufferIndex] = '\0';
            bufferIndex = 0;
            // Signal that a command is ready
            return;
        } else if (bufferIndex < SERIAL_BUFFER_SIZE - 1) {
            buffer[bufferIndex++] = c;
        } else {
            // Buffer overflow
            clearBuffer();
        }
    }
}

bool SerialHandler::hasCommand() {
    return (buffer[0] != '\0');
}

const char* SerialHandler::getBuffer() {
    return buffer;
}

void SerialHandler::clearBuffer() {
    bufferIndex = 0;
    memset(buffer, 0, SERIAL_BUFFER_SIZE);
}

CommandType SerialHandler::getCommandType(const char* cmdBuffer) {
    if (strncmp(cmdBuffer, "MODE", 4) == 0) {
        return CMD_MODE;
    } else if (strncmp(cmdBuffer, "SERVO", 5) == 0) {
        return CMD_SERVO;
    } else if (strncmp(cmdBuffer, "STEPPER", 7) == 0) {
        return CMD_STEPPER;
    }
    return CMD_UNKNOWN;
}

GameMode SerialHandler::parseModeName(const char* modeName) {
    if (strcmp(modeName, "VALORANT") == 0) {
        return MODE_VALORANT;
    } else if (strcmp(modeName, "RACING") == 0) {
        return MODE_RACING;
    }
    return MODE_NONE;
}

bool SerialHandler::parseModeCommand(char* cmdBuffer, ModeCommand& cmd, GameMode& mode) {
    // Expected format: "MODE,SET,VALORANT" or "MODE,START" or "MODE,STOP" or "MODE,RESET" or "MODE,STATUS"
    
    if (strncmp(cmdBuffer, "MODE,", 5) != 0) {
        return false;
    }
    
    char* ptr = cmdBuffer + 5;
    
    if (strncmp(ptr, "SET,", 4) == 0) {
        cmd = MODE_CMD_SET;
        ptr += 4;
        mode = parseModeName(ptr);
        return (mode != MODE_NONE);
    } else if (strcmp(ptr, "START") == 0) {
        cmd = MODE_CMD_START;
        return true;
    } else if (strcmp(ptr, "STOP") == 0) {
        cmd = MODE_CMD_STOP;
        return true;
    } else if (strcmp(ptr, "RESET") == 0) {
        cmd = MODE_CMD_RESET;
        return true;
    } else if (strcmp(ptr, "STATUS") == 0) {
        cmd = MODE_CMD_STATUS;
        return true;
    }
    
    cmd = MODE_CMD_UNKNOWN;
    return false;
}

bool SerialHandler::parseServoCommand(char* cmdBuffer, BatchServoCommand& servoCmd) {
    // Expected format: "SERVO,LJX,LJY,RJX,RJY,TRIGGER[,DURATION]"
    // Example: "SERVO,90,90,90,90,0,200"
    
    if (strncmp(cmdBuffer, "SERVO,", 6) != 0) {
        return false;
    }
    
    char* ptr = cmdBuffer + 6;
    int values[6] = {0};
    int count = 0;
    
    // Create a copy since strtok modifies the string
    char tempBuffer[SERIAL_BUFFER_SIZE];
    strncpy(tempBuffer, ptr, SERIAL_BUFFER_SIZE - 1);
    tempBuffer[SERIAL_BUFFER_SIZE - 1] = '\0';
    
    char* token = strtok(tempBuffer, ",");
    
    while (token != NULL && count < 6) {
        values[count] = atoi(token);
        count++;
        token = strtok(NULL, ",");
    }
    
    // Must have at least 5 values (without duration)
    if (count < 5) {
        return false;
    }
    
    // Validate ranges
    if (values[0] < 0 || values[0] > 180 ||  // LJ_X
        values[1] < 0 || values[1] > 180 ||  // LJ_Y
        values[2] < 0 || values[2] > 180 ||  // RJ_X
        values[3] < 0 || values[3] > 180 ||  // RJ_Y
        values[4] < 0 || values[4] > 180) {  // TRIGGER
        return false;
    }
    
    servoCmd.lj_x = values[0];
    servoCmd.lj_y = values[1];
    servoCmd.rj_x = values[2];
    servoCmd.rj_y = values[3];
    servoCmd.trigger = values[4];
    
    // Duration is optional
    if (count >= 6) {
        servoCmd.duration_ms = values[5];
        if (servoCmd.duration_ms < MIN_MOVEMENT_DURATION_MS || 
            servoCmd.duration_ms > MAX_MOVEMENT_DURATION_MS) {
            return false;
        }
    } else {
        servoCmd.duration_ms = DEFAULT_MOVEMENT_DURATION_MS;
    }
    
    return true;
}

bool SerialHandler::parseStepperCommand(char* cmdBuffer, StepperCommand& stepperCmd) {
    // Expected format: "STEPPER,LEFT[,RATE_HZ]", "STEPPER,RIGHT[,RATE_HZ]", or "STEPPER,STOP"
    if (strncmp(cmdBuffer, "STEPPER,", 8) != 0) {
        return false;
    }

    char* ptr = cmdBuffer + 8;
    char tempBuffer[SERIAL_BUFFER_SIZE];
    strncpy(tempBuffer, ptr, SERIAL_BUFFER_SIZE - 1);
    tempBuffer[SERIAL_BUFFER_SIZE - 1] = '\0';

    char* token = strtok(tempBuffer, ",");
    if (token == NULL) {
        return false;
    }

    if (strcmp(token, "STOP") == 0) {
        stepperCmd.direction = STEPPER_DIR_STOP;
        stepperCmd.rate_hz = 0;
        return true;
    }

    if (strcmp(token, "LEFT") == 0) {
        stepperCmd.direction = STEPPER_DIR_LEFT;
    } else if (strcmp(token, "RIGHT") == 0) {
        stepperCmd.direction = STEPPER_DIR_RIGHT;
    } else {
        return false;
    }

    token = strtok(NULL, ",");
    if (token == NULL || token[0] == '\0') {
        stepperCmd.rate_hz = DEFAULT_STEPPER_RATE_HZ;
        return true;
    }

    int rateHz = atoi(token);
    if (rateHz < MIN_STEPPER_RATE_HZ || rateHz > MAX_STEPPER_RATE_HZ) {
        return false;
    }

    stepperCmd.rate_hz = static_cast<uint16_t>(rateHz);
    return true;
}
