#ifndef FLASH_FAT_H
#define FLASH_FAT_H
#include <stdint.h>
#include <stdbool.h>

void storage_init(void);

// Letture/scritture a blocchi da 512 byte (granularita' MSC).
// La write NON tocca la flash: accumula in una cache da 4 KB.
bool storage_read (uint32_t lba, uint32_t offset, void *buf, uint32_t len);
bool storage_write(uint32_t lba, uint32_t offset, const void *buf, uint32_t len);

// Committa la cache. Da chiamare SOLO dal main loop, mai da un callback USB.
void storage_flush(void);
bool storage_dirty(void);

// Richiesta di flush differita (safe da chiamare nei callback MSC).
void storage_request_flush(void);
void storage_flush_task(void);

// Cancella la partizione. Distruttivo.
void storage_format(void);

#endif
