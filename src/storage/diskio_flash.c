/*
 * diskio_flash.c - glue FatFs -> flash_fat
 *
 * Serve solo in HOST mode, per rileggere payload.bin da dentro il Pico.
 * In DEVICE mode il filesystem lo manipola l'host via MSC e FatFs non
 * viene nemmeno montato: i due accessi non sono mai contemporanei,
 * che e' precisamente il caveat che i FAT12 embedded non sanno gestire.
 */
#include <string.h>
#include "ff.h"
#include "diskio.h"
#include "config.h"
#include "flash_fat.h"

DSTATUS disk_status(BYTE pdrv) {
    return (pdrv == 0) ? 0 : STA_NOINIT;
}

DSTATUS disk_initialize(BYTE pdrv) {
    if (pdrv != 0) return STA_NOINIT;
    storage_init();
    return 0;
}

DRESULT disk_read(BYTE pdrv, BYTE *buff, LBA_t sector, UINT count) {
    if (pdrv != 0) return RES_PARERR;
    for (UINT i = 0; i < count; i++) {
        if (!storage_read(sector + i, 0, buff + i * DISK_BLOCK_SIZE, DISK_BLOCK_SIZE))
            return RES_ERROR;
    }
    return RES_OK;
}

DRESULT disk_write(BYTE pdrv, const BYTE *buff, LBA_t sector, UINT count) {
    if (pdrv != 0) return RES_PARERR;
    for (UINT i = 0; i < count; i++) {
        if (!storage_write(sector + i, 0, buff + i * DISK_BLOCK_SIZE, DISK_BLOCK_SIZE))
            return RES_ERROR;
    }
    return RES_OK;
}

DRESULT disk_ioctl(BYTE pdrv, BYTE cmd, void *buff) {
    if (pdrv != 0) return RES_PARERR;
    switch (cmd) {
        case CTRL_SYNC:
            storage_flush();
            return RES_OK;
        case GET_SECTOR_COUNT:
            *(LBA_t *)buff = DISK_BLOCK_COUNT;
            return RES_OK;
        case GET_SECTOR_SIZE:
            *(WORD *)buff = DISK_BLOCK_SIZE;
            return RES_OK;
        case GET_BLOCK_SIZE:
            // In unita' di settori: dice a FatFs di allineare il FAT
            // ai settori di cancellazione, riducendo le riscritture.
            *(DWORD *)buff = FLASH_SECTOR_BYTES / DISK_BLOCK_SIZE;
            return RES_OK;
        default:
            return RES_PARERR;
    }
}

DWORD get_fattime(void) {
    // Nessun RTC alimentato: data fissa. Irrilevante per un solo file.
    return ((DWORD)(2025 - 1980) << 25) | ((DWORD)1 << 21) | ((DWORD)1 << 16);
}
