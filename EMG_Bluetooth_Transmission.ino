#include "Arduino.h"
#include "EMGFilters.h"
#include <Servo.h>
#include <SoftwareSerial.h>

// Pin and option configuration

/** Analog pin for EMG input (after analog frontend). */
#define SensorInputPin A0

/** Enable USB debug logging (1 = enabled, 0 = disabled). */
#define TIMING_DEBUG 1

/** SoftwareSerial for HM-10 BLE: Arduino RX=D2, TX=D3. */
SoftwareSerial BTserial(2, 3); // RX, TX (from Arduino’s perspective)

// Objects

/** EMG filter object: HP + Notch (50Hz) + LP. */
EMGFilters myFilter;

/** Array of 5 servos (for example: finger joints of a prosthesis). */
Servo myServos[5];

// EMG processing parameters

/** Sample rate parameter used for filter design. */
int sampleRate = SAMPLE_FREQ_1000HZ;

/** Notch filter frequency (50 Hz for EU mains). */
int humFreq = NOTCH_FREQ_50HZ;

/** Threshold for EMG envelope detection (empirical). */
static int Threshold = 600;

/** Timestamp of last detected EMG activity (ms). */
unsigned long lastEMGSignalTime = 0;

/** Timeout (ms) after last EMG activity before servos return to rest. */
const int EMGSignalTimeout = 1300;

// Setup

void setup() {
    // Initialize EMG filter: (fs, notch, enableHP, enableNotch, enableLP)
    // This sets filter coefficients, not the actual loop timing.
    myFilter.init(sampleRate, humFreq, true, true, true);

    // Initialize serial interfaces
    BTserial.begin(9600);     // BLE HM-10
    Serial.begin(115200);     // USB debug

    // Attach servos to pins 9–13
    myServos[0].attach(9);
    myServos[1].attach(10);
    myServos[2].attach(11);
    myServos[3].attach(12);
    myServos[4].attach(13);

    // Optional: set all servos to rest position at startup
    for (int i = 0; i < 5; i++) {
        myServos[i].write(0);
    }
}

// Main loop

void loop() {
    // 1) Acquire EMG signal (ADC)
    int Value = analogRead(SensorInputPin);  

    // 2) Apply filtering
    int DataAfterFilter = myFilter.update(Value);

    // 3) Envelope detection: square the signal
    // NOTE: sq(int) returns long. Assigned here to int, which may overflow.
    int envelope = sq(DataAfterFilter);

    // Apply thresholding: values below threshold set to 0
    envelope = (envelope > Threshold) ? envelope : 0;

    // 4) Send raw EMG value to BLE (HM-10)
    BTserial.println(Value);

    // 5) Optional debug over USB
    if (TIMING_DEBUG) {
        Serial.print("EMG raw: ");
        Serial.println(Value);
        // Optionally: print filtered value and envelope
    }

    // 6) Servo control logic
    if (envelope > Threshold) {
        // EMG activity detected → move all servos to active position
        for (int i = 0; i < 5; i++) {
            myServos[i].write(180);
        }
        lastEMGSignalTime = millis(); // update activity timestamp
    } else {
        // If inactivity lasts longer than timeout → move back to rest
        if (millis() - lastEMGSignalTime > EMGSignalTimeout) {
            for (int i = 0; i < 5; i++) {
                myServos[i].write(0);
            }
        }
    }

    // 7) Loop pacing (~2 kHz effective rate with this delay)
    delayMicroseconds(500);
}
