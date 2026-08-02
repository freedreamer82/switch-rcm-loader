/*
 * rcm_host.c
 *
 * Enumeration and target filtering. The send trigger is NOT a button: it is
 * the appearance of a device with the APX VID/PID. The target dictates the
 * timing, and the VID/PID filter is the only thing keeping the payload from
 * being fired into some random USB stick.
 *
 * Logging goes to UART (GPIO0, 115200). You will not have it in the field,
 * but during development it is the only window available: the USB port
 * belongs to the target, not to a console.
 */
#include <stdio.h>
#include <string.h>
#include <tusb.h>
#include <pico/stdlib.h>
#include <hardware/structs/usb.h>
#include "config.h"
#include "status.h"
#include "rcm_host.h"
#include "rcm_proto.h"

typedef enum {
    H_IDLE,        // nothing attached
    H_WRONG_DEV,   // a device is present, but it is not the target
    H_READY,       // target latched, endpoints open
    H_INJECTING,
    H_DONE,
    H_FAILED
} host_state_t;

static host_state_t state = H_IDLE;
static uint8_t  dev_addr  = 0;
static uint8_t  ep_out    = 0;
static uint8_t  ep_in     = 0;

// Transfer completion: TinyUSB is asynchronous, and these flags make it
// synchronous in the main loop without dragging in an RTOS.
static volatile bool     xfer_done = false;
static volatile bool     xfer_ok   = false;
static volatile uint32_t xfer_len  = 0;

// The final trigger has its own flags, separate from the bulk ones. What is
// kept here is TinyUSB's raw result rather than a bool: it is needed to tell
// a stall from a timeout (see rcm_xfer_t).
static volatile bool          trigger_done   = false;
static volatile xfer_result_t trigger_result = XFER_RESULT_INVALID;

static rcm_bulk_fault_t last_fault = BULK_OK;
rcm_bulk_fault_t rcm_last_bulk_fault(void) { return last_fault; }

uint8_t rcm_dev_addr(void) { return dev_addr; }

// ------------------------------------------------------------- callbacks

static void xfer_cb(tuh_xfer_t *xfer) {
    xfer_ok   = (xfer->result == XFER_RESULT_SUCCESS);
    xfer_len  = xfer->actual_len;
    xfer_done = true;
}

static void trigger_cb(tuh_xfer_t *xfer) {
    trigger_result = xfer->result;
    trigger_done   = true;
}

const char *rcm_xfer_name(rcm_xfer_t r) {
    switch (r) {
    case RCM_XFER_OK:      return "ok";
    case RCM_XFER_TIMEOUT: return "timeout";
    case RCM_XFER_STALLED: return "stalled";
    case RCM_XFER_FAILED:  return "failed";
    default:               return "?";
    }
}

/*
 * Find the bulk endpoints by READING the device, instead of assuming them.
 *
 * This used to hardcode 0x01/0x81 at 64 bytes on the grounds that "the
 * bootrom always exposes this pair". That assumption costs nothing to check
 * and everything to get wrong: a wrong endpoint number still enumerates
 * fine over EP0 and then NAKs every bulk transfer forever, which looks
 * exactly like a dead target.
 */
static bool open_bulk_endpoints(uint8_t addr) {
    static uint8_t cfg_buf[CFG_TUH_ENUMERATION_BUFSIZE];
    ep_out = ep_in = 0;

    if (tuh_descriptor_get_configuration_sync(addr, 0, cfg_buf, sizeof(cfg_buf))
        != XFER_RESULT_SUCCESS) {
        printf("[host] failed to read the configuration descriptor\n");
        status_error(ERR_TARGET);
        return false;
    }

    tusb_desc_configuration_t const *cfg = (tusb_desc_configuration_t const *)cfg_buf;
    uint16_t total = tu_le16toh(cfg->wTotalLength);
    if (total > sizeof(cfg_buf)) total = sizeof(cfg_buf);
    printf("[host] configuration descriptor: %u bytes, %u interface(s)\n",
           total, cfg->bNumInterfaces);

    uint8_t const *p   = cfg_buf + cfg->bLength;
    uint8_t const *end = cfg_buf + total;
    const tusb_desc_endpoint_t *d_out = NULL, *d_in = NULL;

    while (p + 2 <= end && p[0] >= 2 && p + p[0] <= end) {
        if (p[1] == TUSB_DESC_ENDPOINT) {
            const tusb_desc_endpoint_t *e = (const tusb_desc_endpoint_t *)p;
            printf("[host]   EP 0x%02x type %u mps %u\n",
                   e->bEndpointAddress, e->bmAttributes.xfer,
                   tu_edpt_packet_size(e));
            if (e->bmAttributes.xfer == TUSB_XFER_BULK) {
                if (tu_edpt_dir(e->bEndpointAddress) == TUSB_DIR_OUT) {
                    if (!d_out) d_out = e;
                } else {
                    if (!d_in) d_in = e;
                }
            }
        }
        p += p[0];
    }

    if (!d_out || !d_in) {
        printf("[host] no bulk IN+OUT pair in the descriptor\n");
        status_error(ERR_TARGET);
        return false;
    }

    if (!tuh_edpt_open(addr, d_out)) {
        printf("[host] could not open EP OUT 0x%02x\n", d_out->bEndpointAddress);
        return false;
    }
    if (!tuh_edpt_open(addr, d_in)) {
        printf("[host] could not open EP IN 0x%02x\n", d_in->bEndpointAddress);
        return false;
    }

    ep_out = d_out->bEndpointAddress;
    ep_in  = d_in->bEndpointAddress;
    printf("[host] bulk endpoints: OUT 0x%02x  IN 0x%02x  (mps %u/%u)\n",
           ep_out, ep_in, tu_edpt_packet_size(d_out), tu_edpt_packet_size(d_in));
    return true;
}

void tuh_mount_cb(uint8_t addr) {
    uint16_t vid = 0, pid = 0;
    tuh_vid_pid_get(addr, &vid, &pid);
    printf("[host] device at addr %u: %04x:%04x\n", addr, vid, pid);

    if (vid != APX_VID || pid != APX_PID) {
        // Anything else is ignored, deliberately.
        printf("[host] not the target (expected %04x:%04x) - ignoring\n",
               APX_VID, APX_PID);
        state = H_WRONG_DEV;
        status_set(ST_HOST_WRONG);
        return;
    }

    dev_addr = addr;
    if (!open_bulk_endpoints(addr)) {
        printf("[host] endpoint setup failed\n");
        state = H_FAILED;
        status_error(ERR_TARGET);
        return;
    }
    // A settling pause before the first transfer. The mount callback runs
    // microseconds after SET_CONFIGURATION completes, and a bootrom is not
    // obliged to have its bulk endpoints armed that quickly.
    sleep_ms(RCM_SETTLE_MS);
    printf("[host] target latched (after %u ms settle)\n", RCM_SETTLE_MS);
    state = H_READY;
}

void tuh_umount_cb(uint8_t addr) {
    if (addr != dev_addr) return;
    printf("[host] device detached (addr %u)\n", addr);
    dev_addr = ep_in = ep_out = 0;
    // After a successful injection the target detaches: that is normal, and
    // we do not go back to waiting, so the send cannot be repeated.
    if (state != H_DONE) {
        state = H_IDLE;
        status_set(ST_HOST_WAIT);
    }
}

// ------------------------------------------------------------- transfers

/*
 * The endpoint has to be passed in so a timeout can CANCEL the transfer.
 *
 * Returning without cancelling is a trap: the transfer stays queued inside
 * TinyUSB and its callback fires later, landing on the flags of the NEXT
 * transfer and making a perfectly good bulk OUT report whatever the
 * abandoned one ended up doing. It is not hypothetical - the device-ID read
 * is explicitly allowed to time out, so the very next call is the first
 * packet of the payload, which then fails for no reason.
 */
static bool wait_xfer(uint8_t ep_addr, uint32_t timeout_ms) {
    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    while (!xfer_done) {
        tuh_task();                       // completion is delivered from here
        if (to_ms_since_boot(get_absolute_time()) - t0 > timeout_ms) {
            /*
             * Dump the controller state before giving up. Everything in the
             * HCD looks correct on paper, so the question is no longer what
             * the driver intends but what the silicon actually did: is the
             * async endpoint enabled, is a buffer armed, did the bus report
             * an error. Guessing has been tried.
             */
            printf("[host] --- USB registers at timeout ---\n");
            printf("[host]  sie_status   %08lx\n", (unsigned long)usb_hw->sie_status);
            printf("[host]  sie_ctrl     %08lx\n", (unsigned long)usb_hw->sie_ctrl);
            printf("[host]  int_ep_ctrl  %08lx\n", (unsigned long)usb_hw->int_ep_ctrl);
            printf("[host]  dev_addr_ctl %08lx\n", (unsigned long)usb_hw->dev_addr_ctrl);
            printf("[host]  buf_status   %08lx\n", (unsigned long)usb_hw->buf_status);
            for (int i = 0; i < 2; i++) {
                printf("[host]  intep%d addr %08lx ctrl %08lx buf %08lx\n", i,
                       (unsigned long)usb_hw->int_ep_addr_ctrl[i],
                       (unsigned long)usbh_dpram->int_ep_ctrl[i].ctrl,
                       (unsigned long)usbh_dpram->int_ep_buffer_ctrl[i].ctrl);
            }
            printf("[host] -----------------------------\n");
            tuh_edpt_abort_xfer(dev_addr, ep_addr);
            // A completion may have slipped in between the test and the
            // abort: start the next transfer from a clean slate.
            xfer_done = false;
            printf("[host] transfer on EP 0x%02x timed out (%lu ms), cancelled\n",
                   ep_addr, (unsigned long)timeout_ms);
            last_fault = BULK_TIMEOUT;
            return false;
        }
    }
    if (!xfer_ok) {
        printf("[host] transfer on EP 0x%02x completed with an error\n", ep_addr);
        last_fault = BULK_XFER_ERR;
    }
    return xfer_ok;
}

bool rcm_bulk_out(const void *data, uint32_t len, uint32_t timeout_ms) {
    if (!ep_out) { last_fault = BULK_NO_EP; return false; }
    last_fault = BULK_OK;
    xfer_done = false;
    tuh_xfer_t xfer = {
        .daddr       = dev_addr,
        .ep_addr     = ep_out,
        .buflen      = len,
        .buffer      = (uint8_t *)data,
        .complete_cb = xfer_cb,
        .user_data   = 0
    };
    if (!tuh_edpt_xfer(&xfer)) {
        printf("[host] tuh_edpt_xfer OUT refused\n");
        last_fault = BULK_REJECTED;
        return false;
    }
    return wait_xfer(ep_out, timeout_ms);
}

bool rcm_bulk_in(void *data, uint32_t len, uint32_t timeout_ms) {
    if (!ep_in) { last_fault = BULK_NO_EP; return false; }
    last_fault = BULK_OK;
    xfer_done = false;
    tuh_xfer_t xfer = {
        .daddr       = dev_addr,
        .ep_addr     = ep_in,
        .buflen      = len,
        .buffer      = (uint8_t *)data,
        .complete_cb = xfer_cb,
        .user_data   = 0
    };
    if (!tuh_edpt_xfer(&xfer)) {
        printf("[host] tuh_edpt_xfer IN refused\n");
        last_fault = BULK_REJECTED;
        return false;
    }
    return wait_xfer(ep_in, timeout_ms);
}

/*
 * The control transfer used as the final trigger, SYNCHRONOUS.
 *
 * MIND THE CALLBACK: in TinyUSB, complete_cb == NULL does NOT mean "fire and
 * forget", it means a BLOCKING transfer on an OSAL semaphore that would never
 * be signalled here, because no other context calls tuh_task() - with NULL
 * the firmware would hang. A non-null callback is required, and the wait is
 * done by hand while pumping tuh_task(), the same shape as wait_xfer for the
 * bulk transfers.
 *
 * It does not decide what counts as an error: it just reports the outcome.
 * For the RCM trigger a timeout is the normal outcome of a successful
 * injection, and that policy lives in rcm_proto.c, not here.
 */
rcm_xfer_t rcm_control_out(uint8_t bmRequestType, uint8_t bRequest,
                           uint16_t wValue, uint16_t wIndex, uint16_t wLength,
                           uint32_t timeout_ms) {
    // static: the transfer is asynchronous and TinyUSB may read these
    // buffers after this function has returned.
    //
    // The size is NOT arbitrary: the trigger is an IN with wLength 0x7000,
    // and TinyUSB writes into the buffer whatever the device delivers before
    // it dies. A buffer shorter than the largest wLength passed here is
    // random memory corruption.
    static CFG_TUH_MEM_SECTION CFG_TUH_MEM_ALIGN uint8_t scratch[RCM_TRIGGER_WLENGTH];
    static tusb_control_request_t req;

    if (wLength > sizeof(scratch)) {
        printf("[host] trigger: wLength 0x%04x exceeds the buffer (0x%x)\n",
               wLength, (unsigned)sizeof(scratch));
        return RCM_XFER_FAILED;
    }

    req = (tusb_control_request_t){
        .bmRequestType = bmRequestType,
        .bRequest      = bRequest,
        .wValue        = wValue,
        .wIndex        = wIndex,
        .wLength       = wLength
    };

    tuh_xfer_t xfer = {
        .daddr       = dev_addr,
        .ep_addr     = 0,
        .setup       = &req,
        .buffer      = scratch,
        .complete_cb = trigger_cb,     // NOT NULL: see the comment above
        .user_data   = 0
    };

    trigger_done   = false;
    trigger_result = XFER_RESULT_INVALID;
    printf("[host] trigger: bRequest 0x%02x wLength 0x%04x\n", bRequest, wLength);

    if (!tuh_control_xfer(&xfer)) {
        printf("[host] tuh_control_xfer refused\n");
        return RCM_XFER_FAILED;
    }

    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    while (!trigger_done) {
        tuh_task();
        if (to_ms_since_boot(get_absolute_time()) - t0 > timeout_ms) {
            // Same reasoning as wait_xfer: leave nothing queued on ep0.
            tuh_edpt_abort_xfer(dev_addr, 0);
            trigger_done = false;
            printf("[host] trigger: no answer within %lu ms\n",
                   (unsigned long)timeout_ms);
            return RCM_XFER_TIMEOUT;
        }
    }

    switch (trigger_result) {
    case XFER_RESULT_SUCCESS: return RCM_XFER_OK;
    case XFER_RESULT_STALLED: return RCM_XFER_STALLED;
    case XFER_RESULT_TIMEOUT: return RCM_XFER_TIMEOUT;
    default:                  return RCM_XFER_FAILED;
    }
}

// ------------------------------------------------------------- loop

void rcm_host_init(void) {
    state = H_IDLE;
    status_set(ST_HOST_WAIT);
    printf("[host] HOST mode, waiting for a device (target %04x:%04x)\n",
           APX_VID, APX_PID);
    tuh_init(BOARD_TUH_RHPORT);
}

void rcm_host_task(void) {
    tuh_task();

    if (state == H_READY) {
        state = H_INJECTING;
        status_set(ST_SENDING);

        uint32_t t0 = to_ms_since_boot(get_absolute_time());
        bool ok = rcm_proto_inject();
        uint32_t dt = to_ms_since_boot(get_absolute_time()) - t0;

        printf("[host] injection %s in %lu ms\n",
               ok ? "completed" : "FAILED", (unsigned long)dt);

        state = ok ? H_DONE : H_FAILED;
        // On failure rcm_proto_inject has already blinked out the cause;
        // overwriting it with a generic ST_ERROR would throw that away.
        if (ok) status_set(ST_DONE);
    }
}
