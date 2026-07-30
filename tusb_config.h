#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#define CFG_TUSB_MCU              OPT_MCU_RP2040
#define CFG_TUSB_OS               OPT_OS_PICO
#define CFG_TUSB_DEBUG            0

// Entrambi gli stack compilati; solo uno viene inizializzato al boot.
// Vedi README: e' il punto da validare per primo sulla tua versione
// di TinyUSB. Con -DFORCE_ROLE=host|device si compila un ruolo solo.
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

// Buffer MSC: 4096 allinea i trasferimenti al settore di cancellazione,
// cosi' una write dell'host tocca un solo settore invece di due.
#define CFG_TUD_MSC_EP_BUFSIZE    4096

// ---------------------------------------------------------- host
#define CFG_TUH_ENUMERATION_BUFSIZE 256
#define CFG_TUH_HUB               0    // niente hub: collegamento diretto
#define CFG_TUH_CDC               0
#define CFG_TUH_HID               0
#define CFG_TUH_MSC               0
#define CFG_TUH_VENDOR            0
#define CFG_TUH_DEVICE_MAX        1
// Endpoint aperti a mano con tuh_edpt_open() per il device vendor-specific.
#define CFG_TUH_ENDPOINT_MAX      4

#endif
