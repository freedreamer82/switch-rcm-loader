/*
 * main.c
 *
 * There is a single USB controller, so the role is picked at boot and never
 * changes. MODE_PIN is a plain jumper to GND: closed selects HOST, open
 * selects DEVICE.
 *
 * Fail-safe: contact open = DEVICE. Forget the jumper and the result is
 * "sent nothing", not "sent a payload into an unknown device".
 */
#include <pico/stdlib.h>
#include <tusb.h>
#include "config.h"
#include "mode.h"
#include "status.h"
#include "storage/flash_fat.h"
#include "storage/fs_setup.h"

#if !defined(FORCE_ROLE_HOST) && !defined(FORCE_ROLE_DEVICE)
  #define ROLE_RUNTIME 1
#endif

#if CFG_TUH_ENABLED
#include "host/rcm_host.h"
#endif

#if CFG_TUD_ENABLED
static void run_device_mode(void) {
    storage_init();
    if (!fs_ensure_formatted()) {
        status_set(ST_ERROR);
        while (true) status_task();
    }
    tud_init(BOARD_TUD_RHPORT);
    status_set(ST_MSC_IDLE);

    while (true) {
        tud_task();
        // The flash commit lives here, outside the callbacks: erasing a
        // sector blocks for ~40 ms with interrupts off, and doing that
        // inside tud_msc_write10_cb would choke the USB ISR.
        storage_flush_task();
        if (!storage_dirty()) status_set(ST_MSC_IDLE);
        status_task();
    }
}
#endif

#if CFG_TUH_ENABLED
static void run_host_mode(void) {
    storage_init();
    rcm_host_init();

    while (true) {
        rcm_host_task();
        status_task();
    }
}
#endif

int main(void) {
    stdio_init_all();
    status_init();

    // Three flashes: proof that the firmware runs, before any USB.
    for (int i = 0; i < 40; i++) { status_task(); sleep_ms(15); }

    run_mode_t mode = mode_read();

#if defined(FORCE_ROLE_HOST)
    (void)mode;
    run_host_mode();
#elif defined(FORCE_ROLE_DEVICE)
    (void)mode;
    run_device_mode();
#else
    if (mode == MODE_HOST) run_host_mode();
    else                   run_device_mode();
#endif

    return 0;
}
