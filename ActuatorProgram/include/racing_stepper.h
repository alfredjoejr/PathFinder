#ifndef RACING_STEPPER_H
#define RACING_STEPPER_H

#include <Arduino.h>
#include "protocol.h"

class RacingStepper {
public:
	static void init();
	static void update();
	static void start(StepperDirection direction, uint16_t rateHz = DEFAULT_STEPPER_RATE_HZ);
	static void stop();
	static bool isActive();

private:
	static void setDirection(StepperDirection direction);
	static void setStepPin(bool high);
};

#endif
