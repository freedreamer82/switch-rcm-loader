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
    case RCM_XFER_STALLED: return "stallata";
    case RCM_XFER_FAILED:  return "fallita";
    default:               return "?";
    }
}

/*
 * The APX bootrom's endpoints. The device is vendor-specific: no TinyUSB
 * class driver claims it, so the endpoints are opened by hand.
 *
 * These are FIXED addresses, not looked up in the configuration descriptor.
 * The bootrom always exposes this pair and nothing else, and reading the
 * descriptor would only add a failure point for no gain: if that read fails
 * the injection is lost for nothing.
 */
static const tusb_desc_endpoint_t apx_ep_out_desc = {
    .bLength          = sizeof(tusb_desc_endpoint_t),
    .bDescriptorType  = TUSB_DESC_ENDPOINT,
    .bEndpointAddress = APX_EP_OUT,
    .bmAttributes     = { .xfer = TUSB_XFER_BULK },
    .wMaxPacketSize   = APX_EP_SIZE,
    .bInterval        = 0,
};

static const tusb_desc_endpoint_t apx_ep_in_desc = {
    .bLength          = sizeof(tusb_desc_endpoint_t),
    .bDescriptorType  = TUSB_DESC_ENDPOINT,
    .bEndpointAddress = APX_EP_IN,
    .bmAttributes     = { .xfer = TUSB_XFER_BULK },
    .wMaxPacketSize   = APX_EP_SIZE,
    .bInterval        = 0,
};

static bool open_bulk_endpoints(uint8_t addr) {
    ep_out = ep_in = 0;

    if (!tuh_edpt_open(addr, &apx_ep_out_desc)) {
        printf("[host] apertura EP OUT 0x%02x fallita\n", APX_EP_OUT);
        return false;
    }
    if (!tuh_edpt_open(addr, &apx_ep_in_desc)) {
        printf("[host] apertura EP IN 0x%02x fallita\n", APX_EP_IN);
        return false;
    }

    ep_out = APX_EP_OUT;
    ep_in  = APX_EP_IN;
    printf("[host] endpoint bulk: OUT 0x%02x  IN 0x%02x\n", ep_out, ep_in);
    return true;
}

void tuh_mount_cb(uint8_t addr) {
    uint16_t vid = 0, pid = 0;
    tuh_vid_pid_get(addr, &vid, &pid);
    printf("[host] device su addr %u: %04x:%04x\n", addr, vid, pid);

    if (vid != APX_VID || pid != APX_PID) {
        // Anything else is ignored, deliberately.
        printf("[host] non e' il target (attesi %04x:%04x) - ignoro\n",
               APX_VID, APX_PID);
        state = H_WRONG_DEV;
        status_set(ST_HOST_WRONG);
        return;
    }

    dev_addr = addr;
    if (!open_bulk_endpoints(addr)) {
        printf("[host] apertura endpoint fallita\n");
        state = H_FAILED;
        status_set(ST_ERROR);
        return;
    }
    printf("[host] target agganciato\n");
    state = H_READY;
}

void tuh_umount_cb(uint8_t addr) {
    if (addr != dev_addr) return;
    printf("[host] device sganciato (addr %u)\n", addr);
    dev_addr = ep_in = ep_out = 0;
    // After a successful injection the target detaches: that is normal, and
    // we do not go back to waiting, so the send cannot be repeated.
    if (state != H_DONE) {
        state = H_IDLE;
        status_set(ST_HOST_WAIT);
    }
}

// ------------------------------------------------------------- transfers

static bool wait_xfer(uint32_t timeout_ms) {
    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    while (!xfer_done) {
        tuh_task();                       // completion is delivered from here
        if (to_ms_since_boot(get_absolute_time()) - t0 > timeout_ms) {
            printf("[host] timeout transfer (%lu ms)\n", (unsigned long)timeout_ms);
            return false;
        }
    }
    return xfer_ok;
}

bool rcm_bulk_out(const void *data, uint32_t len, uint32_t timeout_ms) {
    if (!ep_out) return false;
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
        printf("[host] tuh_edpt_xfer OUT rifiutata\n");
        return false;
    }
    return wait_xfer(timeout_ms);
}

bool rcm_bulk_in(void *data, uint32_t len, uint32_t timeout_ms) {
    if (!ep_in) return false;
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
        printf("[host] tuh_edpt_xfer IN rifiutata\n");
        return false;
    }
    return wait_xfer(timeout_ms);
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
        printf("[host] trigger: wLength 0x%04x oltre il buffer (0x%x)\n",
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
        printf("[host] tuh_control_xfer rifiutata\n");
        return RCM_XFER_FAILED;
    }

    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    while (!trigger_done) {
        tuh_task();
        if (to_ms_since_boot(get_absolute_time()) - t0 > timeout_ms) {
            printf("[host] trigger: nessuna risposta in %lu ms\n",
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
    printf("[host] modo HOST, attendo un device (target %04x:%04x)\n",
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

        printf("[host] iniezione %s in %lu ms\n",
               ok ? "completata" : "FALLITA", (unsigned long)dt);

        state = ok ? H_DONE : H_FAILED;
        status_set(ok ? ST_DONE : ST_ERROR);
    }
}
