#ifndef STATUS_H
#define STATUS_H

// The LED is the whole interface: powered from a power bank there is no
// serial console. Every state has a pattern you can tell apart by eye.
// In DEVICE it always blinks; in HOST on = armed, off = payload sent,
// blinking = trouble.
typedef enum {
    ST_BOOT,          // 3 quick flashes at start-up, before the role is known
    ST_MSC_IDLE,      // DEVICE: slow blink, drive is mountable
    ST_MSC_BUSY,      // DEVICE: fast blink, writing - do not unplug
    ST_HOST_WAIT,     // HOST: solid on, armed and waiting for the target
    ST_HOST_WRONG,    // HOST: slow blink, a non-APX device is being ignored
    ST_SENDING,       // HOST: off, transfer in progress
    ST_DONE,          // HOST: off, payload sent
    ST_ERROR          // continuous fast flashing: error
} status_t;

void status_init(void);
void status_set(status_t s);
void status_task(void);   // non-blocking, call it from the main loop

#endif
