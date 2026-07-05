#ifndef MODE_MANAGER_H
#define MODE_MANAGER_H

#include <Arduino.h>
#include "protocol.h"

class ModeManager {
private:
    static ModeState currentState;
    static GameMode currentMode;
    static unsigned long lastCommandTime;

public:
    // Initialize mode manager
    static void init();
    
    // Set the game mode (MODE,SET,<mode>)
    static bool setMode(GameMode mode);
    
    // Start the current game mode (MODE,START)
    static bool startMode();
    
    // Stop the current game mode (MODE,STOP)
    static bool stopMode();

    // Reset back to IDLE after stopping (MODE,RESET)
    static bool resetToIdle();
    
    // Check timeout (call periodically in main loop)
    static void checkTimeout();
    
    // Query current state
    static ModeState getState();
    static GameMode getMode();
    
    // Reset last command time (call when command received)
    static void updateCommandTime();
    
    // Helper: Check if servo commands are allowed (only in RUNNING state)
    static bool isServoCommandAllowed();

    // Helper: Check if racing stepper commands are allowed
    static bool isStepperCommandAllowed();
    
private:
    // Internal state transition handler
    static bool transitionTo(ModeState newState);
};

#endif
