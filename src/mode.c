#include <pico/stdlib.h>
#include "config.h"
#include "mode.h"

run_mode_t mode_read(void) {
    gpio_init(MODE_PIN);
    gpio_set_dir(MODE_PIN, GPIO_IN);
    gpio_pull_up(MODE_PIN);

    // See config.h: the park pin's reset state is a pull-down, so leaving it
    // alone would make the parked cap read as a half level rather than open.
    gpio_init(MODE_PARK_PIN);
    gpio_set_dir(MODE_PARK_PIN, GPIO_IN);
    gpio_pull_up(MODE_PARK_PIN);

    // The internal pull-up is weak (~50k): give it time to charge the
    // capacitance of the flying lead before sampling.
    sleep_ms(5);

    // 16 samples that have to agree. An oxidised or half-seated jumper is
    // exactly the failure you do not want to get wrong.
    int low = 0;
    for (int i = 0; i < 16; i++) {
        if (!gpio_get(MODE_PIN)) low++;
        sleep_us(200);
    }

    return (low >= 14) ? MODE_HOST : MODE_DEVICE;
}
