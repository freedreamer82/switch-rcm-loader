#include <pico/stdlib.h>
#include "config.h"
#include "status.h"

static status_t current = ST_BOOT;
static uint32_t phase_start = 0;
static uint8_t  err_code = 1;

void status_init(void) {
    gpio_init(STATUS_LED_PIN);
    gpio_set_dir(STATUS_LED_PIN, GPIO_OUT);
    phase_start = to_ms_since_boot(get_absolute_time());
}

void status_set(status_t s) {
    if (s == current) return;
    current = s;
    phase_start = to_ms_since_boot(get_absolute_time());
}

// Does not go through status_set: the phase has to restart even if we are
// already in ST_ERROR, otherwise a second cause would blink out of step.
void status_error(status_err_t code) {
    err_code = (uint8_t)(code ? code : 1);
    current  = ST_ERROR;
    phase_start = to_ms_since_boot(get_absolute_time());
}

/*
 * Patterns are expressed as (period, function of the time within it).
 *
 * The two roles read differently on purpose:
 *
 *   DEVICE  always blinking. There is no "idle" look: as long as it
 *           blinks, the drive is alive.
 *   HOST    on = armed, off = payload went out, blinking = trouble.
 *           The point is that at a glance "the light went out" means done,
 *           which is the only thing you want to know with the target in
 *           your hand.
 */
void status_task(void) {
    uint32_t t = to_ms_since_boot(get_absolute_time()) - phase_start;
    bool on = false;

    switch (current) {
        // Before the role is known: three flashes, the firmware is running.
        case ST_BOOT:       on = (t % 200) < 100 && t < 600;      break;

        // DEVICE: always blinking, faster while writing.
        case ST_MSC_IDLE:   on = (t % 1000) < 500;                break;
        case ST_MSC_BUSY:   on = (t % 200) < 100;                 break;

        // HOST: solid on until the payload has been sent.
        case ST_HOST_WAIT:  on = true;                            break;
        case ST_SENDING:    on = false;                           break;
        case ST_DONE:       on = false;                           break;

        // HOST, trouble: blinking. Slow when the device is not APX (it gets
        // ignored and we stay armed).
        case ST_HOST_WRONG: on = (t % 600) < 300;                 break;

        // Errors blink out their cause: err_code flashes of 200 ms, then a
        // one-second gap. Counting flashes beats needing a serial cable in
        // the field, and the LED cannot do colour.
        case ST_ERROR: {
            uint32_t burst  = err_code * 400u;
            uint32_t k      = t % (burst + 1000u);
            on = (k < burst) && ((k % 400u) < 200u);
            break;
        }
    }
    gpio_put(STATUS_LED_PIN, on);
}
