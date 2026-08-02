#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#define CFG_TUSB_MCU              OPT_MCU_RP2040
#define CFG_TUSB_OS               OPT_OS_PICO
#define CFG_TUSB_DEBUG            0

// Both stacks are compiled in; only one gets initialised at boot.
// See the README: this is the first thing to validate against your version
// of TinyUSB. With -DFORCE_ROLE=host|device only one role is compiled.
#ifdef FORCE_ROLE_HOST
  #define CFG_TUD_ENABLED         0
  #define CFG_TUH_ENABLED         1
#elif defined(FORCE_ROLE_DEVICE)
  #define CFG_TUD_ENABLED         1
  #define CFG_TUH_ENABLED         0
#else
  #define CFG_TUD_ENABLED         1
  #define CFG_TUH_ENABLED         1
#endif

#define CFG_TUD_MAX_SPEED         OPT_MODE_FULL_SPEED
#define CFG_TUH_MAX_SPEED         OPT_MODE_FULL_SPEED

#ifndef CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_SECTION
#endif
#ifndef CFG_TUSB_MEM_ALIGN
#define CFG_TUSB_MEM_ALIGN        __attribute__ ((aligned(4)))
#endif

// ---------------------------------------------------------- device
#define CFG_TUD_ENDPOINT0_SIZE    64
#define CFG_TUD_MSC               1
#define CFG_TUD_CDC               0
#define CFG_TUD_HID               0
#define CFG_TUD_MIDI              0
#define CFG_TUD_VENDOR            0

// MSC buffer: 4096 aligns transfers to the erase sector, so one host write
// touches a single sector instead of two.
#define CFG_TUD_MSC_EP_BUFSIZE    4096

// ---------------------------------------------------------- host

// MANDATORY here, and it defaults to 0.
//
// The APX bootrom is vendor-specific, so no class driver owns its endpoints
// and every bulk transfer goes through tuh_edpt_xfer() with our own
// completion callback. That whole path is compiled out unless this is 1:
// usbh.c does not even declare the ep_callback array (line ~135), does not
// store the callback in tuh_edpt_xfer() (~916), and does not invoke it when
// the transfer completes (~561).
//
// With it at 0 the failure is silent and thoroughly misleading: the transfer
// really happens, the data really lands in the endpoint buffer, the bus
// reports no error - and the stack simply never tells you. It looks exactly
// like a target that will not answer. Control transfers keep working the
// whole time, because those take the epnum == 0 branch, which is always
// compiled in.
#define CFG_TUH_API_EDPT_XFER     1

#define CFG_TUH_ENUMERATION_BUFSIZE 256
#define CFG_TUH_HUB               0    // no hubs: direct connection
#define CFG_TUH_CDC               0
#define CFG_TUH_HID               0
#define CFG_TUH_MSC               0
#define CFG_TUH_VENDOR            0
#define CFG_TUH_DEVICE_MAX        1
// Endpoints are opened by hand with tuh_edpt_open() for the vendor-specific
// device.
#define CFG_TUH_ENDPOINT_MAX      4

#endif
