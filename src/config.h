/*
 * config.h - configurazione hardware e layout flash
 */
#ifndef CONFIG_H
#define CONFIG_H

// ---------------------------------------------------------------- pin
// Contatto meccanicamente accoppiato al jumper di alimentazione.
// Chiuso verso GND = HOST mode (jumper su pin 40 / VBUS).
// Aperto (pull-up interno) = DEVICE mode -> fail-safe.
#define MODE_PIN            15
#define STATUS_LED_PIN      PICO_DEFAULT_LED_PIN

// ---------------------------------------------------------------- flash
// Pico 2 MB: [0x000000 .. 0x100000) firmware, [0x100000 .. 0x200000) FAT12.
// Se usi un Pico con flash diversa, aggiorna solo queste due.
#define FS_FLASH_OFFSET     (1024u * 1024u)
#define FS_FLASH_SIZE       (1024u * 1024u)

#define FLASH_SECTOR_BYTES  4096u
#define DISK_BLOCK_SIZE     512u
#define DISK_BLOCK_COUNT    (FS_FLASH_SIZE / DISK_BLOCK_SIZE)

// Millisecondi di inattivita' USB dopo i quali si committa la cache in flash.
#define FLUSH_IDLE_MS       750

// ---------------------------------------------------------------- payload
#define PAYLOAD_FILENAME    "payload.bin"

// ---------------------------------------------------------------- target
// Nvidia Tegra APX (bootrom in recovery mode)
#define APX_VID             0x0955
#define APX_PID             0x7321

// Endpoint bulk del bootrom. Fissi: il bootrom espone sempre e solo
// questa coppia, quindi non si va a cercarli nel descrittore.
#define APX_EP_OUT          0x01
#define APX_EP_IN           0x81
#define APX_EP_SIZE         64


// Un solo root hub port sull'RP2040. Definiti qui per non trascinarsi
// dietro il BSP di TinyUSB (bsp/board_api.h) in un progetto custom.
#ifndef BOARD_TUD_RHPORT
#define BOARD_TUD_RHPORT 0
#endif
#ifndef BOARD_TUH_RHPORT
#define BOARD_TUH_RHPORT 0
#endif

#endif
