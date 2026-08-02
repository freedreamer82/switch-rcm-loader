/*
 * diskio_flash.c - FatFs -> flash_fat glue
 *
 * Only needed in HOST mode, to read payload.bin back from inside the Pico.
 * In DEVICE mode the filesystem is manipulated by the host over MSC and
 * FatFs is not even mounted: the two accessors are never simultaneous,
 * which is precisely the caveat embedded FAT12 setups cannot handle.
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
            // In units of sectors: tells FatFs to align the FAT to the
            // erase sectors, which cuts down on rewrites.
            *(DWORD *)buff = FLASH_SECTOR_BYTES / DISK_BLOCK_SIZE;
            return RES_OK;
        default:
            return RES_PARERR;
    }
}

DWORD get_fattime(void) {
    // No battery-backed RTC: fixed date. Irrelevant for a single file.
    return ((DWORD)(2025 - 1980) << 25) | ((DWORD)1 << 21) | ((DWORD)1 << 16);
}
