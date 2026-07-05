#include "response_builder.h"

void ResponseBuilder::init(uint32_t baudRate) {
    Serial.begin(baudRate);
    delay(100);
}

void ResponseBuilder::sendOK() {
    Serial.println("OK");
}

void ResponseBuilder::sendError(uint16_t errorCode, const char* message) {
    Serial.print("ERR,");
    Serial.print(errorCode);
    Serial.print(",");
    Serial.println(message);
}

void ResponseBuilder::sendStatus(GameMode mode, ModeState state) {
    Serial.print("STATUS,");
    
    // Send mode name
    switch (mode) {
        case MODE_VALORANT:
            Serial.print("VALORANT");
            break;
        case MODE_RACING:
            Serial.print("RACING");
            break;
        default:
            Serial.print("NONE");
    }
    
    Serial.print(",");
    
    // Send state name
    switch (state) {
        case STATE_IDLE:
            Serial.println("IDLE");
            break;
        case STATE_MODE_SET:
            Serial.println("MODE_SET");
            break;
        case STATE_RUNNING:
            Serial.println("RUNNING");
            break;
        case STATE_STOPPED:
            Serial.println("STOPPED");
            break;
        default:
            Serial.println("UNKNOWN");
    }
}

void ResponseBuilder::sendDebug(const char* message) {
    Serial.print("DEBUG,");
    Serial.println(message);
}

void ResponseBuilder::sendResponse(const char* prefix, const char* data) {
    Serial.print(prefix);
    Serial.println(data);
}
