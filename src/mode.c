#include <pico/stdlib.h>
#include "config.h"
#include "mode.h"

run_mode_t mode_read(void) {
    gpio_init(MODE_PIN);
    gpio_set_dir(MODE_PIN, GPIO_IN);
    gpio_pull_up(MODE_PIN);

    // Il pull-up interno e' debole (~50k): dagli tempo di caricare la
    // capacita' del filo volante prima di campionare.
    sleep_ms(5);

    // 16 campioni concordi, altrimenti si riparte. Un jumper ossidato o
    // mezzo inserito e' esattamente il caso che non vuoi sbagliare.
    int low = 0;
    for (int i = 0; i < 16; i++) {
        if (!gpio_get(MODE_PIN)) low++;
        sleep_us(200);
    }

    return (low >= 14) ? MODE_HOST : MODE_DEVICE;
}
