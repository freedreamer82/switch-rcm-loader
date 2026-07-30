/*
 * flash_fat.c
 *
 * Blocchi da 512 byte su una flash che si cancella a settori da 4096.
 * Tre problemi, tre soluzioni:
 *
 *  1. granularita': cache read-modify-write da un settore intero
 *  2. XIP: le letture arrivano dal mapping XIP (nessuna copia inutile),
 *     le scritture passano dalla SDK che gira in RAM
 *  3. timing: cancellare un settore blocca ~40 ms con le interruzioni
 *     disabilitate, quindi non si committa dentro un callback USB ma
 *     nel main loop, a bus fermo
 */
#include <string.h>
#include <hardware/flash.h>
#include <hardware/sync.h>
#include <pico/stdlib.h>
#include "config.h"
#include "flash_fat.h"

#define XIP_FS_BASE  ((const uint8_t *)(XIP_BASE + FS_FLASH_OFFSET))

static uint8_t  cache[FLASH_SECTOR_BYTES];
static uint32_t cache_sector = UINT32_MAX;   // indice settore, non indirizzo
static bool     cache_dirty  = false;
static volatile bool flush_pending = false;
static uint32_t last_write_ms = 0;

void storage_init(void) {
    cache_sector = UINT32_MAX;
    cache_dirty  = false;
}

bool storage_dirty(void) { return cache_dirty; }

// Deve stare in RAM. Nota bene: __not_in_flash_func NON implica noinline,
// quindi con -O3 GCC la inlinava dentro storage_flush() (che vive in flash)
// e l'attributo di sezione veniva silenziosamente buttato via: nessun
// warning, simbolo assente dall'ELF. __no_inline_not_in_flash_func e' la
// variante che il pico-sdk fornisce esattamente per questo caso.
//
// Onestamente: la parte che regge davvero e' che flash_range_erase/program
// dell'SDK sono gia' RAM-resident e che qui le interruzioni sono spente.
// Tenere anche il wrapper in RAM e' difensivo, ma soprattutto rende
// verificabile l'intenzione con arm-none-eabi-nm.
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
    // Committa se l'host ha chiesto un sync, oppure dopo un po' di
    // silenzio: evita di cancellare un settore mentre l'host ci scrive.
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

    // Se il settore richiesto e' quello sporco in cache, si serve da la':
    // altrimenti l'host rileggerebbe dalla flash dati gia' superati.
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

    // Una write MSC da 512 byte non attraversa mai un confine da 4 KB,
    // ma FatFs puo' scrivere multi-blocco: spezzo per sicurezza.
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
