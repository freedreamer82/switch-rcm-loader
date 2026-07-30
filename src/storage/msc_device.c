/*
 * msc_device.c - callback USB Mass Storage
 *
 * Nota su dove gira questo codice: TinyUSB chiama questi callback da
 * dentro tud_task(), quindi dal main loop, NON dall'ISR. Scrivere in
 * flash qui sarebbe tecnicamente legale ma bloccherebbe l'ISR USB per
 * ~40 ms a settore. Percio' write10 accumula e il commit lo fa
 * storage_flush_task() quando il bus e' fermo.
 */
#include <string.h>
#include <tusb.h>
#include "config.h"
#include "status.h"
#include "flash_fat.h"

// Opcode SCSI standard (SYNCHRONIZE CACHE (10)). Definito qui invece di
// usare l'enum di TinyUSB perche' il nome del simbolo e' cambiato tra
// versioni: 0x35 non cambia mai.
#define SCSI_OPCODE_SYNC_CACHE_10  0x35

#define MSC_VENDOR   "PicoRCM "
#define MSC_PRODUCT  "PayloadStore   "
#define MSC_REV      "1.0 "

void tud_msc_inquiry_cb(uint8_t lun, uint8_t vid[8], uint8_t pid[16], uint8_t rev[4]) {
    (void)lun;
    memcpy(vid, MSC_VENDOR,  8);
    memcpy(pid, MSC_PRODUCT, 16);
    memcpy(rev, MSC_REV,     4);
}

bool tud_msc_test_unit_ready_cb(uint8_t lun) {
    (void)lun;
    return true;
}

void tud_msc_capacity_cb(uint8_t lun, uint32_t *block_count, uint16_t *block_size) {
    (void)lun;
    *block_count = DISK_BLOCK_COUNT;
    *block_size  = DISK_BLOCK_SIZE;
}

// L'eject dell'host e' il momento piu' affidabile per committare.
bool tud_msc_start_stop_cb(uint8_t lun, uint8_t power_condition,
                           bool start, bool load_eject) {
    (void)lun; (void)power_condition;
    if (load_eject && !start) {
        storage_request_flush();
    }
    return true;
}

int32_t tud_msc_read10_cb(uint8_t lun, uint32_t lba, uint32_t offset,
                          void *buffer, uint32_t bufsize) {
    (void)lun;
    if (lba >= DISK_BLOCK_COUNT) return -1;
    if (!storage_read(lba, offset, buffer, bufsize)) return -1;
    return (int32_t)bufsize;
}

int32_t tud_msc_write10_cb(uint8_t lun, uint32_t lba, uint32_t offset,
                           uint8_t *buffer, uint32_t bufsize) {
    (void)lun;
    if (lba >= DISK_BLOCK_COUNT) return -1;
    status_set(ST_MSC_BUSY);
    if (!storage_write(lba, offset, buffer, bufsize)) return -1;
    return (int32_t)bufsize;
}

bool tud_msc_is_writable_cb(uint8_t lun) {
    (void)lun;
    return true;
}

int32_t tud_msc_scsi_cb(uint8_t lun, uint8_t const scsi_cmd[16],
                        void *buffer, uint16_t bufsize) {
    (void)lun; (void)buffer; (void)bufsize;
    switch (scsi_cmd[0]) {
        case SCSI_OPCODE_SYNC_CACHE_10:
            // L'host ha finito di scrivere: e' il segnale che aspettavamo.
            storage_request_flush();
            return 0;
        default:
            tud_msc_set_sense(lun, SCSI_SENSE_ILLEGAL_REQUEST, 0x20, 0x00);
            return -1;
    }
}
