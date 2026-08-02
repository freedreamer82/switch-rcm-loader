#ifndef RCM_HOST_H
#define RCM_HOST_H
#include <stdbool.h>
#include <stdint.h>

void rcm_host_init(void);
void rcm_host_task(void);

// Synchronous bulk transfers to the mounted device.
// They return false on timeout or stall.
bool rcm_bulk_out(const void *data, uint32_t len, uint32_t timeout_ms);
bool rcm_bulk_in (void *data, uint32_t len, uint32_t timeout_ms);
/*
 * Outcome of a control transfer. These are four distinct cases and they must
 * NOT be flattened into a bool at this level: for the RCM trigger a timeout
 * is the normal outcome of a successful injection, whereas a stall is the
 * real failure. The caller decides what counts as an error; the transport
 * layer only reports what it saw.
 */
typedef enum {
    RCM_XFER_OK = 0,      // completed, status stage closed
    RCM_XFER_TIMEOUT,     // no answer within the timeout
    RCM_XFER_STALLED,     // the device rejected the request
    RCM_XFER_FAILED,      // never even started, or a driver error
} rcm_xfer_t;

const char *rcm_xfer_name(rcm_xfer_t r);

// Synchronous control transfer: waits up to timeout_ms while pumping
// tuh_task(). Despite the name it follows the direction encoded in
// bmRequestType, and the RCM trigger is an IN transfer.
rcm_xfer_t rcm_control_out(uint8_t bmRequestType, uint8_t bRequest,
                           uint16_t wValue, uint16_t wIndex, uint16_t wLength,
                           uint32_t timeout_ms);

// Why the last bulk transfer failed. Set by rcm_bulk_out/rcm_bulk_in on
// every call, so the caller can report something more useful than "failed".
typedef enum {
    BULK_OK = 0,
    BULK_NO_EP,      // the endpoint was never opened
    BULK_REJECTED,   // tuh_edpt_xfer refused to start it
    BULK_TIMEOUT,    // started, no completion within the timeout
    BULK_XFER_ERR,   // completed, but the result was not SUCCESS
} rcm_bulk_fault_t;

rcm_bulk_fault_t rcm_last_bulk_fault(void);

uint8_t rcm_dev_addr(void);

#endif
