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

// Error codes, blinked out as a count. The LED is a single green one, so the
// cause is carried by how many flashes you see, not by colour: N flashes,
// then a one-second pause, repeating forever.
typedef enum {
    ERR_FS_FORMAT     = 1,   // the FAT could not be created at boot
    ERR_FAT_MOUNT     = 2,   // f_mount failed in host mode
    ERR_NO_PAYLOAD    = 3,   // payload.bin not found
    ERR_PAYLOAD_EMPTY = 4,   // payload.bin is zero bytes
    ERR_PAYLOAD_BIG   = 5,   // payload.bin over RCM_PAYLOAD_MAX
    ERR_BULK          = 6,   // a bulk OUT failed or timed out mid-send
    ERR_TRIGGER       = 7,   // the target rejected the trigger: no overflow
    ERR_ENDPOINTS     = 8,   // tuh_edpt_open failed on the APX endpoints
    ERR_BULK_FIRST    = 9,   // the first bulk OUT failed, cause unknown
    // Codes 10-13 break down a first-packet failure. Without a serial cable
    // these are the only way to see which of the three things went wrong.
    ERR_BULK_NO_EP    = 10,  // ep_out was never opened
    ERR_BULK_REJECTED = 11,  // tuh_edpt_xfer refused to start the transfer
    ERR_BULK_TIMEOUT  = 12,  // started, but never completed within 2 s
    ERR_BULK_XFERERR  = 13,  // completed, but the result was not SUCCESS
    // The device-ID read, which the protocol puts BEFORE the write.
    ERR_DEVID_TIMEOUT = 14,  // the bootrom never delivered the 16 bytes
    ERR_DEVID_OTHER   = 15,  // the read was rejected or errored
    // Endpoint discovery, replacing the old hardcoded 0x01/0x81 assumption.
    ERR_CFG_DESC      = 16,  // could not read the configuration descriptor
    ERR_NO_BULK_EPS   = 17,  // no bulk IN+OUT pair found in the descriptor
} status_err_t;

void status_init(void);
void status_set(status_t s);

// Goes to ST_ERROR and remembers which cause to blink out.
void status_error(status_err_t code);

void status_task(void);   // non-blocking, call it from the main loop

#endif
