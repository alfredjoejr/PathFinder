#include "racing_stepper.h"

namespace {
constexpr uint32_t STEP_PULSE_WIDTH_US = 5;

struct StepperState {
    bool active;
    bool stepPinHigh;
    StepperDirection direction;
    uint16_t rateHz;
    unsigned long lastEdgeMicros;
    int32_t position;
};

StepperState stepperState = {
    false,
    false,
    STEPPER_DIR_STOP,
    DEFAULT_STEPPER_RATE_HZ,
    0,
    0
};
}  // namespace

void RacingStepper::init() {
    pinMode(STEPPER_STEP_PIN, OUTPUT);
    pinMode(STEPPER_DIR_PIN, OUTPUT);

    digitalWrite(STEPPER_STEP_PIN, LOW);
    digitalWrite(STEPPER_DIR_PIN, LOW);

    stepperState.active = false;
    stepperState.stepPinHigh = false;
    stepperState.direction = STEPPER_DIR_STOP;
    stepperState.rateHz = DEFAULT_STEPPER_RATE_HZ;
    stepperState.lastEdgeMicros = micros();
    stepperState.position = 0;
}

void RacingStepper::start(StepperDirection direction, uint16_t rateHz) {
    if (direction == STEPPER_DIR_STOP) {
        stop();
        return;
    }

    if (rateHz < MIN_STEPPER_RATE_HZ) {
        rateHz = MIN_STEPPER_RATE_HZ;
    } else if (rateHz > MAX_STEPPER_RATE_HZ) {
        rateHz = MAX_STEPPER_RATE_HZ;
    }

    setDirection(direction);
    stepperState.direction = direction;
    stepperState.rateHz = rateHz;
    stepperState.active = true;
    stepperState.stepPinHigh = false;
    stepperState.lastEdgeMicros = micros();
    setStepPin(false);
}

void RacingStepper::stop() {
    stepperState.active = false;
    stepperState.direction = STEPPER_DIR_STOP;
    stepperState.stepPinHigh = false;
    setStepPin(false);
}

void RacingStepper::update() {
    if (!stepperState.active) {
        return;
    }

    // Check travel limits: stop pulsing if at or beyond limit in current direction
    if (stepperState.direction == STEPPER_DIR_LEFT && stepperState.position <= -STEPPER_MAX_POSITION_STEPS) {
        if (stepperState.stepPinHigh) {
            setStepPin(false);
            stepperState.stepPinHigh = false;
        }
        return;
    }
    if (stepperState.direction == STEPPER_DIR_RIGHT && stepperState.position >= STEPPER_MAX_POSITION_STEPS) {
        if (stepperState.stepPinHigh) {
            setStepPin(false);
            stepperState.stepPinHigh = false;
        }
        return;
    }

    unsigned long now = micros();
    uint32_t stepIntervalUs = 1000000UL / stepperState.rateHz;

    if (!stepperState.stepPinHigh) {
        if (now - stepperState.lastEdgeMicros >= stepIntervalUs) {
            setStepPin(true);
            stepperState.stepPinHigh = true;
            stepperState.lastEdgeMicros = now;

            // Track position on rising step pulse
            if (stepperState.direction == STEPPER_DIR_LEFT) {
                stepperState.position--;
            } else if (stepperState.direction == STEPPER_DIR_RIGHT) {
                stepperState.position++;
            }
        }
    } else {
        if (now - stepperState.lastEdgeMicros >= STEP_PULSE_WIDTH_US) {
            setStepPin(false);
            stepperState.stepPinHigh = false;
            stepperState.lastEdgeMicros = now;
        }
    }
}

bool RacingStepper::isActive() {
    return stepperState.active;
}

int32_t RacingStepper::getPosition() {
    return stepperState.position;
}

void RacingStepper::resetPosition() {
    stepperState.position = 0;
}

void RacingStepper::setDirection(StepperDirection direction) {
    switch (direction) {
        case STEPPER_DIR_LEFT:
            digitalWrite(STEPPER_DIR_PIN, LOW);
            break;
        case STEPPER_DIR_RIGHT:
            digitalWrite(STEPPER_DIR_PIN, HIGH);
            break;
        default:
            digitalWrite(STEPPER_DIR_PIN, LOW);
            break;
    }
}

void RacingStepper::setStepPin(bool high) {
    digitalWrite(STEPPER_STEP_PIN, high ? HIGH : LOW);
}
