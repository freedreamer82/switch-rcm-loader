/*
 * flash_fat.c
 *
 * 512-byte blocks on a flash that erases in 4096-byte sectors.
 * Three problems, three answers:
 *
 *  1. granularity: a read-modify-write cache holding one whole sector
 *  2. XIP: reads come straight from the XIP mapping (no pointless copy),
 *     writes go through the SDK routines that run from RAM
 *  3. timing: erasing a sector blocks for ~40 ms with interrupts
 *     disabled, so the commit does not happen inside a USB callback but
 *     in the main loop, with the bus quiet
 */
#include <string.h>
#include <hardware/flash.h>
#include <hardware/sync.h>
#include <pico/stdlib.h>
#include "config.h"
#include "flash_fat.h"

#define XIP_FS_BASE  ((const uint8_t *)(XIP_BASE + FS_FLASH_OFFSET))

static uint8_t  cache[FLASH_SECTOR_BYTES];
static uint32_t cache_sector = UINT32_MAX;   // sector index, not an address
static bool     cache_dirty  = false;
static volatile bool flush_pending = false;
static uint32_t last_write_ms = 0;

void storage_init(void) {
    cache_sector = UINT32_MAX;
    cache_dirty  = false;
}

bool storage_dirty(void) { return cache_dirty; }

// This has to live in RAM. Note carefully: __not_in_flash_func does NOT
// imply noinline, so at -O3 GCC would inline it into storage_flush() (which
// lives in flash) and the section attribute was silently dropped: no
// warning, symbol absent from the ELF. __no_inline_not_in_flash_func is the
// variant the pico-sdk provides for exactly this case.
//
// Honestly: what really holds this up is that the SDK's
// flash_range_erase/program are already RAM-resident and that interrupts are
// off here. Keeping the wrapper in RAM too is defensive, but above all it
// makes the intent verifiable with arm-none-eabi-nm.
static void __no_inline_not_in_flash_func(commit_sector)(uint32_t sector) {
    uint32_t off = FS_FLASH_OFFSET + sector * FLASH_SECTOR_BYTES;
    uint32_t ints = save_and_disable_interrupts();
    flash_range_erase(off, FLASH_SECTOR_BYTES);
    flash_range_program(off, cache, FLASH_SECTOR_BYTES);
    restore_interrupts(ints);
}

void storage_flush(void) {
    if (!cache_dirty || cache_sector == UINT32_MAX) {
        cache_dirty = false;
        flush_pending = false;
        return;
    }
    commit_sector(cache_sector);
    cache_dirty = false;
    flush_pending = false;
}

void storage_request_flush(void) { flush_pending = true; }

void storage_flush_task(void) {
    if (!cache_dirty) return;
    uint32_t now = to_ms_since_boot(get_absolute_time());
    // Commit if the host asked for a sync, or after a stretch of silence:
    // this avoids erasing a sector while the host is still writing to it.
    if (flush_pending || (now - last_write_ms) > FLUSH_IDLE_MS) {
        storage_flush();
    }
}

static void load_sector(uint32_t sector) {
    if (cache_sector == sector) return;
    if (cache_dirty) storage_flush();
    memcpy(cache, XIP_FS_BASE + sector * FLASH_SECTOR_BYTES, FLASH_SECTOR_BYTES);
    cache_sector = sector;
}

bool storage_read(uint32_t lba, uint32_t offset, void *buf, uint32_t len) {
    uint32_t addr = lba * DISK_BLOCK_SIZE + offset;
    if (addr + len > FS_FLASH_SIZE) return false;

    uint32_t sector = addr / FLASH_SECTOR_BYTES;

    // If the requested sector is the dirty one in cache, serve it from
    // there: otherwise the host would read back stale data from flash.
    if (cache_dirty && sector == cache_sector &&
        (addr % FLASH_SECTOR_BYTES) + len <= FLASH_SECTOR_BYTES) {
        memcpy(buf, cache + (addr % FLASH_SECTOR_BYTES), len);
    } else {
        memcpy(buf, XIP_FS_BASE + addr, len);
    }
    return true;
}

bool storage_write(uint32_t lba, uint32_t offset, const void *buf, uint32_t len) {
    uint32_t addr = lba * DISK_BLOCK_SIZE + offset;
    if (addr + len > FS_FLASH_SIZE) return false;

    // A 512-byte MSC write never crosses a 4 KB boundary, but FatFs can
    // write multi-block: split it to be safe.
    while (len) {
        uint32_t sector = addr / FLASH_SECTOR_BYTES;
        uint32_t in_sec = addr % FLASH_SECTOR_BYTES;
        uint32_t chunk  = FLASH_SECTOR_BYTES - in_sec;
        if (chunk > len) chunk = len;

        load_sector(sector);
        memcpy(cache + in_sec, buf, chunk);
        cache_dirty = true;

        addr += chunk;
        buf   = (const uint8_t *)buf + chunk;
        len  -= chunk;
    }
    last_write_ms = to_ms_since_boot(get_absolute_time());
    return true;
}

void storage_format(void) {
    uint32_t ints = save_and_disable_interrupts();
    flash_range_erase(FS_FLASH_OFFSET, FS_FLASH_SIZE);
    restore_interrupts(ints);
    cache_sector = UINT32_MAX;
    cache_dirty  = false;
}
