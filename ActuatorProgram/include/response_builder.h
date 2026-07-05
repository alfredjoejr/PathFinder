#ifndef RESPONSE_BUILDER_H
#define RESPONSE_BUILDER_H

#include <Arduino.h>
#include "protocol.h"

class ResponseBuilder {
public:
    // Initialize serial communication
    static void init(uint32_t baudRate = SERIAL_BAUD_RATE);
    
    // Send OK response
    static void sendOK();
    
    // Send error response with code and message
    static void sendError(uint16_t errorCode, const char* message);
    
    // Send status response
    static void sendStatus(GameMode mode, ModeState state);
    
    // Send debug message (optional)
    static void sendDebug(const char* message);
    
private:
    // Helper to send formatted response
    static void sendResponse(const char* prefix, const char* data);
};

#endif
