/*
 * config.h - hardware configuration and flash layout
 */
#ifndef CONFIG_H
#define CONFIG_H

// ---------------------------------------------------------------- pins
// GPIO14 is physical pin 19, which sits next to the GND on pin 18: a plain
// 2-way jumper across 18-19 selects the role.
//   closed to GND = HOST mode   (inject)
//   open (internal pull-up) = DEVICE mode -> fail-safe
#define MODE_PIN            14
#define STATUS_LED_PIN      PICO_DEFAULT_LED_PIN

// ---------------------------------------------------------------- flash
// Pico 2 MB: [0x000000 .. 0x100000) firmware, [0x100000 .. 0x200000) FAT12.
// On a Pico with a different flash size, only these two need updating.
#define FS_FLASH_OFFSET     (1024u * 1024u)
#define FS_FLASH_SIZE       (1024u * 1024u)

#define FLASH_SECTOR_BYTES  4096u
#define DISK_BLOCK_SIZE     512u
#define DISK_BLOCK_COUNT    (FS_FLASH_SIZE / DISK_BLOCK_SIZE)

// Milliseconds of USB silence after which the cache is committed to flash.
#define FLUSH_IDLE_MS       750

// ---------------------------------------------------------------- payload
#define PAYLOAD_FILENAME    "payload.bin"

// ---------------------------------------------------------------- target
// Nvidia Tegra APX (bootrom in recovery mode)
#define APX_VID             0x0955
#define APX_PID             0x7321

// The bootrom's bulk endpoints. Hardcoded: the bootrom always exposes this
// pair and nothing else, so there is no point reading the descriptor.
#define APX_EP_OUT          0x01
#define APX_EP_IN           0x81
#define APX_EP_SIZE         64


// The RP2040 has a single root hub port. Defined here so a custom project
// does not have to drag in TinyUSB's BSP (bsp/board_api.h).
#ifndef BOARD_TUD_RHPORT
#define BOARD_TUD_RHPORT 0
#endif
#ifndef BOARD_TUH_RHPORT
#define BOARD_TUH_RHPORT 0
#endif

#endif
