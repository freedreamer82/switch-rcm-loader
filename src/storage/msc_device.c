/*
 * msc_device.c - USB Mass Storage callbacks
 *
 * A note on where this code runs: TinyUSB calls these callbacks from inside
 * tud_task(), so from the main loop, NOT from the ISR. Writing to flash here
 * would be technically legal but would block the USB ISR for ~40 ms per
 * sector. That is why write10 accumulates and the commit is done by
 * storage_flush_task() once the bus goes quiet.
 */
#include <string.h>
#include <tusb.h>
#include "config.h"
#include "status.h"
#include "flash_fat.h"

// Standard SCSI opcode (SYNCHRONIZE CACHE (10)). Defined here rather than
// using TinyUSB's enum because the symbol name changed between versions:
// 0x35 never does.
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

// The host's eject is the most reliable moment to commit.
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
            // The host has finished writing: this is the signal we wanted.
            storage_request_flush();
            return 0;
        default:
            tud_msc_set_sense(lun, SCSI_SENSE_ILLEGAL_REQUEST, 0x20, 0x00);
            return -1;
    }
}
