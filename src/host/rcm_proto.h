#ifndef RCM_PROTO_H
#define RCM_PROTO_H
#include <stdbool.h>
#include <stdint.h>

// ===================================================================
//  PROTOCOL CONSTANTS
// ===================================================================
//
//  Canonical source: fusee-launcher (Katherine Temkin / ReSwitched),
//  fusee-launcher.py + intermezzo.s. The Fusee Gelee paper (April 2018)
//  documents the why; fusee-launcher documents the how.
//
//  The resulting memory map, in the target's IRAM:
//
//    0x40010000  start of the message BODY. The 680 header bytes do not
//                land here: the bootrom consumes them to learn how much
//                to read, and the body starts after them.
//    0x40010000 .. 0x4001F000
//                filled entirely with the intermezzo's address
//                (0xF000 bytes = 0x3C00 words). Whichever return address
//                the smash happens to hit, control lands on the
//                intermezzo.
//    0x4001F000  intermezzo (92 bytes): copies the payload from
//                0x40020000 to 0x40010000 and jumps into it.
//    0x40020000  user payload.
//
//  The two constants at the tail of the intermezzo blob (0x40020000 and
//  0x40010000) must match RCM_PAYLOAD_LOAD_BLOCK and RCM_PAYLOAD_ADDR: if
//  you touch these defines, the blob has to be regenerated.
//
#define RCM_CHUNK_SIZE          0x1000u
#define RCM_DEVICE_ID_LEN       16

#define RCM_PAYLOAD_ADDR        0x40010000u
#define RCM_INTERMEZZO_ADDR     0x4001F000u
#define RCM_PAYLOAD_LOAD_BLOCK  0x40020000u

// The length declared in the header: it is the maximum the bootrom will
// accept, and it is exactly why the copy overflows. It is NOT the number
// of bytes actually sent.
#define RCM_MAX_MSG_LEN         0x30298u

// RCM header: 4 bytes of length, then zeros up to 680 (0x2A8).
#define RCM_HEADER_SIZE         680u

// Spray: from the start of the body up to the intermezzo.
#define RCM_SPRAY_BYTES         (RCM_INTERMEZZO_ADDR - RCM_PAYLOAD_ADDR)  /* 0xF000  */
#define RCM_SPRAY_WORDS         (RCM_SPRAY_BYTES / 4u)                    /* 0x3C00  */

// The bootrom's ping-pong copy buffers. Kept purely as documentation: to
// make the last copy land where it must, the parity of the 0x1000 packets
// sent is enough (see the bottom of rcm_proto_inject).
#define RCM_COPY_BUF_LOW        0x40005000u
#define RCM_COPY_BUF_HIGH       0x40009000u

// The final control request: GET_STATUS with an absurd wLength. That read
// is what smashes the bootrom's stack.
#define RCM_TRIGGER_BMREQTYPE   0x81u
#define RCM_TRIGGER_BREQUEST    0x00u    /* TUSB_REQ_GET_STATUS */
#define RCM_TRIGGER_WLENGTH     0x7000u

// The fixed prefix ahead of the payload: header + spray + the 0x1000 block
// holding the intermezzo and its padding.
#define RCM_PREFIX_SIZE   (RCM_HEADER_SIZE + RCM_SPRAY_BYTES + RCM_CHUNK_SIZE)

// End of the Tegra X1's IRAM: 256 KB from 0x40000000. This is the real wall
// the payload size hits, not the length declared in the header. The payload
// lands on RCM_PAYLOAD_LOAD_BLOCK and from there to 0x40040000 there are
// 0x20000 bytes: beyond that, the intermezzo would copy from memory that
// does not exist.
#define RCM_IRAM_END      0x40040000u

// Ceiling for the usable payload: 0x1FFF0 = 131056 bytes. It very nearly
// coincides with the physical space left above the load block, and it is
// also what keeps the total sent close to the declared length. The two
// routes reach the same number, which is a good sign the number is right.
#define RCM_PAYLOAD_MAX   (RCM_MAX_MSG_LEN - RCM_PREFIX_SIZE)

// Runs the whole sequence: reads payload.bin from the FAT12 in flash and
// streams it out. Returns false if the file is missing, too large, or a
// transfer fails.
bool rcm_proto_inject(void);

#endif
