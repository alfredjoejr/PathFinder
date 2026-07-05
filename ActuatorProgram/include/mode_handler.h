#ifndef MODE_HANDLER_H
#define MODE_HANDLER_H

#include <Arduino.h>
#include "protocol.h"
#include "racing_stepper.h"

class ModeHandler {
public:
    // Handle mode-specific initialization when mode starts
    static void onModeStart(GameMode mode);
    
    // Handle mode-specific cleanup when mode stops
    static void onModeStop(GameMode mode);
    
private:
    static void onValorantStart();
    static void onValorantStop();
    static void onRacingStart();
    static void onRacingStop();
};

#endif
