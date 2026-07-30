#include <pico/stdlib.h>
#include "config.h"
#include "status.h"

static status_t current = ST_BOOT;
static uint32_t phase_start = 0;

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

// Pattern espressi come (periodo, funzione del tempo nel periodo).
void status_task(void) {
    uint32_t t = to_ms_since_boot(get_absolute_time()) - phase_start;
    bool on = false;

    switch (current) {
        case ST_BOOT:       on = (t % 200) < 100 && t < 600;      break;
        case ST_MSC_IDLE:   on = (t % 2000) < 120;                break;
        case ST_MSC_BUSY:   on = (t % 100) < 50;                  break;
        case ST_HOST_WAIT:  on = (t % 1000) < 80;                 break;
        case ST_HOST_WRONG: on = ((t % 1200) < 80) ||
                                 ((t % 1200) > 200 && (t % 1200) < 280); break;
        case ST_SENDING:    on = true;                            break;
        case ST_DONE:       on = (t % 2000) < 1700;               break;
        case ST_ERROR:      on = (t % 160) < 80;                  break;
    }
    gpio_put(STATUS_LED_PIN, on);
}
