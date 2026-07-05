#ifndef SERIAL_HANDLER_H
#define SERIAL_HANDLER_H

#include <Arduino.h>
#include "protocol.h"

class SerialHandler {
private:
    static char buffer[SERIAL_BUFFER_SIZE];
    static size_t bufferIndex;

public:
    // Initialize serial communication
    static void init(uint32_t baudRate = SERIAL_BAUD_RATE);
    
    // Check for incoming data and parse commands
    static void update();
    
    // Check if a complete command is available in buffer
    static bool hasCommand();
    
    // Get the command buffer content (read-only)
    static const char* getBuffer();
    
    // Clear the buffer after processing
    static void clearBuffer();
    
    // Parse MODE command: "MODE,SET,VALORANT" or "MODE,START" etc.
    static bool parseModeCommand(char* cmdBuffer, ModeCommand& cmd, GameMode& mode);
    
    // Parse SERVO command: "SERVO,90,90,90,90,0,200"
    static bool parseServoCommand(char* cmdBuffer, BatchServoCommand& servoCmd);

    // Parse STEPPER command: "STEPPER,LEFT[,RATE_HZ]" or "STEPPER,STOP"
    static bool parseStepperCommand(char* cmdBuffer, StepperCommand& stepperCmd);
    
    // Detect command type from buffer
    static CommandType getCommandType(const char* cmdBuffer);
    
private:
    // Internal parsing helpers
    static GameMode parseModeName(const char* modeName);
};

#endif
