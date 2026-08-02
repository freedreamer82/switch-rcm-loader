#ifndef FLASH_FAT_H
#define FLASH_FAT_H
#include <stdint.h>
#include <stdbool.h>

void storage_init(void);

// Reads and writes in 512-byte blocks (the MSC granularity).
// A write does NOT touch flash: it accumulates in a 4 KB cache.
bool storage_read (uint32_t lba, uint32_t offset, void *buf, uint32_t len);
bool storage_write(uint32_t lba, uint32_t offset, const void *buf, uint32_t len);

// Commits the cache. Call ONLY from the main loop, never from a USB callback.
void storage_flush(void);
bool storage_dirty(void);

// Deferred flush request (safe to call from the MSC callbacks).
void storage_request_flush(void);
void storage_flush_task(void);

// Erases the partition. Destructive.
void storage_format(void);

#endif
