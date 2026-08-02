/*
 * fs_setup.c - first-boot formatting
 *
 * Runs ONCE, before tud_init(), so FatFs and MSC are never active at the
 * same time. That is why the concurrent-access problem on FAT12 does not
 * exist in this project: the two accessors are separated in time by
 * construction, not by luck.
 */
#include "ff.h"
#include "diskio.h"
#include "config.h"
#include "flash_fat.h"
#include "fs_setup.h"

static FATFS probe_fs;
static BYTE  work[FF_MAX_SS * 2];

bool fs_ensure_formatted(void) {
    if (f_mount(&probe_fs, "", 1) == FR_OK) {
        f_unmount("");
        return true;    // valid filesystem, leave everything alone
    }

    // Blank flash or corrupt FAT: format.
    storage_format();

    MKFS_PARM opt = {
        .fmt     = FM_FAT | FM_SFD,   // FAT12/16 with no partition table
        .n_fat   = 1,                 // a single FAT copy: fewer writes
        .align   = FLASH_SECTOR_BYTES / DISK_BLOCK_SIZE,
        .n_root  = 32,                // 32 entries: 1-2 are needed
        .au_size = 4096               // cluster = erase sector
    };
    if (f_mkfs("", &opt, work, sizeof(work)) != FR_OK) return false;
    storage_flush();

    if (f_mount(&probe_fs, "", 1) != FR_OK) return false;
    f_setlabel("PICORCM");
    f_unmount("");
    storage_flush();
    return true;
}
