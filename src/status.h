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

// Error classes, blinked out as a count. The LED is a single green one, so
// what you get is N flashes, a one-second pause, and repeat.
//
// Deliberately only four. Anything past five or six flashes cannot be
// counted reliably by eye, and the LED's job is to tell you what to DO, not
// which line of C returned false. The precise reason is printed on the UART
// at every one of these call sites; that is where detail belongs.
typedef enum {
    ERR_PAYLOAD  = 1,   // the filesystem or payload.bin: fix the file
    ERR_TARGET   = 2,   // the target is not talking: cable, RCM, re-seat
    ERR_TRIGGER  = 3,   // it all worked and the console refused the trigger
    ERR_INTERNAL = 4,   // a state that should not be reachable
} status_err_t;

void status_init(void);
void status_set(status_t s);

// Goes to ST_ERROR and remembers which cause to blink out.
void status_error(status_err_t code);

void status_task(void);   // non-blocking, call it from the main loop

#endif
