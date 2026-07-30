/*
 * fs_setup.c - formattazione al primo boot
 *
 * Gira UNA volta, prima di tud_init(), quindi FatFs e MSC non sono mai
 * attivi insieme. E' la ragione per cui in questo progetto il problema
 * dell'accesso concorrente su FAT12 non esiste: i due accessi sono
 * separati nel tempo per costruzione, non per fortuna.
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
        return true;    // filesystem valido, non toccare niente
    }

    // Flash vergine o FAT corrotto: formatta.
    storage_format();

    MKFS_PARM opt = {
        .fmt     = FM_FAT | FM_SFD,   // FAT12/16 senza tabella partizioni
        .n_fat   = 1,                 // una sola copia del FAT: meno scritture
        .align   = FLASH_SECTOR_BYTES / DISK_BLOCK_SIZE,
        .n_root  = 32,                // 32 entry: ne servono 1-2
        .au_size = 4096               // cluster = settore di cancellazione
    };
    if (f_mkfs("", &opt, work, sizeof(work)) != FR_OK) return false;
    storage_flush();

    if (f_mount(&probe_fs, "", 1) != FR_OK) return false;
    f_setlabel("PICORCM");
    f_unmount("");
    storage_flush();
    return true;
}
