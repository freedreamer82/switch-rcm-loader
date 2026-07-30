/*
 * rcm_host.c
 *
 * Enumerazione e filtro del target. Il trigger dell'invio NON e' un
 * pulsante: e' la comparsa di un device con VID/PID APX. Il timing lo
 * detta il target, e il filtro sul VID/PID e' l'unica garanzia di non
 * sparare il payload dentro una chiavetta USB qualsiasi.
 *
 * Log su UART (GPIO0, 115200). In campo non ce l'hai, ma in sviluppo e'
 * l'unica finestra: la porta USB serve al target, non a una console.
 */
#include <stdio.h>
#include <string.h>
#include <tusb.h>
#include <pico/stdlib.h>
#include "config.h"
#include "status.h"
#include "rcm_host.h"
#include "rcm_proto.h"

typedef enum {
    H_IDLE,        // nessun device collegato
    H_WRONG_DEV,   // device presente, non e' il target
    H_READY,       // target agganciato, endpoint aperti
    H_INJECTING,
    H_DONE,
    H_FAILED
} host_state_t;

static host_state_t state = H_IDLE;
static uint8_t  dev_addr  = 0;
static uint8_t  ep_out    = 0;
static uint8_t  ep_in     = 0;

// Completamento dei transfer: TinyUSB e' asincrono, questi flag lo
// rendono sincrono nel main loop senza tirare in mezzo un RTOS.
static volatile bool     xfer_done = false;
static volatile bool     xfer_ok   = false;
static volatile uint32_t xfer_len  = 0;

// Il trigger finale ha i suoi flag, separati da quelli bulk. Qui si
// conserva il result grezzo di TinyUSB, non un bool: serve a distinguere
// stall e timeout (vedi rcm_xfer_t).
static volatile bool          trigger_done   = false;
static volatile xfer_result_t trigger_result = XFER_RESULT_INVALID;

uint8_t rcm_dev_addr(void) { return dev_addr; }

// ------------------------------------------------------------- callback

static void xfer_cb(tuh_xfer_t *xfer) {
    xfer_ok   = (xfer->result == XFER_RESULT_SUCCESS);
    xfer_len  = xfer->actual_len;
    xfer_done = true;
}

static void trigger_cb(tuh_xfer_t *xfer) {
    trigger_result = xfer->result;
    trigger_done   = true;
}

const char *rcm_xfer_name(rcm_xfer_t r) {
    switch (r) {
    case RCM_XFER_OK:      return "ok";
    case RCM_XFER_TIMEOUT: return "timeout";
    case RCM_XFER_STALLED: return "stallata";
    case RCM_XFER_FAILED:  return "fallita";
    default:               return "?";
    }
}

/*
 * Endpoint del bootrom APX. Il device e' vendor-specific: nessun class
 * driver di TinyUSB se ne occupa, gli endpoint si aprono a mano.
 *
 * Sono indirizzi FISSI, non cercati nel descrittore di configurazione.
 * Il bootrom espone sempre e solo questa coppia, e leggere il
 * descrittore aggiunge un punto di rottura che non serve: se quella
 * lettura fallisce si perde l'iniezione per niente.
 */
static const tusb_desc_endpoint_t apx_ep_out_desc = {
    .bLength          = sizeof(tusb_desc_endpoint_t),
    .bDescriptorType  = TUSB_DESC_ENDPOINT,
    .bEndpointAddress = APX_EP_OUT,
    .bmAttributes     = { .xfer = TUSB_XFER_BULK },
    .wMaxPacketSize   = APX_EP_SIZE,
    .bInterval        = 0,
};

static const tusb_desc_endpoint_t apx_ep_in_desc = {
    .bLength          = sizeof(tusb_desc_endpoint_t),
    .bDescriptorType  = TUSB_DESC_ENDPOINT,
    .bEndpointAddress = APX_EP_IN,
    .bmAttributes     = { .xfer = TUSB_XFER_BULK },
    .wMaxPacketSize   = APX_EP_SIZE,
    .bInterval        = 0,
};

static bool open_bulk_endpoints(uint8_t addr) {
    ep_out = ep_in = 0;

    if (!tuh_edpt_open(addr, &apx_ep_out_desc)) {
        printf("[host] apertura EP OUT 0x%02x fallita\n", APX_EP_OUT);
        return false;
    }
    if (!tuh_edpt_open(addr, &apx_ep_in_desc)) {
        printf("[host] apertura EP IN 0x%02x fallita\n", APX_EP_IN);
        return false;
    }

    ep_out = APX_EP_OUT;
    ep_in  = APX_EP_IN;
    printf("[host] endpoint bulk: OUT 0x%02x  IN 0x%02x\n", ep_out, ep_in);
    return true;
}

void tuh_mount_cb(uint8_t addr) {
    uint16_t vid = 0, pid = 0;
    tuh_vid_pid_get(addr, &vid, &pid);
    printf("[host] device su addr %u: %04x:%04x\n", addr, vid, pid);

    if (vid != APX_VID || pid != APX_PID) {
        // Qualsiasi altra cosa viene ignorata, di proposito.
        printf("[host] non e' il target (attesi %04x:%04x) - ignoro\n",
               APX_VID, APX_PID);
        state = H_WRONG_DEV;
        status_set(ST_HOST_WRONG);
        return;
    }

    dev_addr = addr;
    if (!open_bulk_endpoints(addr)) {
        printf("[host] apertura endpoint fallita\n");
        state = H_FAILED;
        status_set(ST_ERROR);
        return;
    }
    printf("[host] target agganciato\n");
    state = H_READY;
}

void tuh_umount_cb(uint8_t addr) {
    if (addr != dev_addr) return;
    printf("[host] device sganciato (addr %u)\n", addr);
    dev_addr = ep_in = ep_out = 0;
    // Dopo un'iniezione riuscita il target si sgancia: e' normale, e non
    // si torna in attesa per non ripetere l'invio.
    if (state != H_DONE) {
        state = H_IDLE;
        status_set(ST_HOST_WAIT);
    }
}

// ------------------------------------------------------------- transfer

static bool wait_xfer(uint32_t timeout_ms) {
    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    while (!xfer_done) {
        tuh_task();                       // il completamento arriva da qui
        if (to_ms_since_boot(get_absolute_time()) - t0 > timeout_ms) {
            printf("[host] timeout transfer (%lu ms)\n", (unsigned long)timeout_ms);
            return false;
        }
    }
    return xfer_ok;
}

bool rcm_bulk_out(const void *data, uint32_t len, uint32_t timeout_ms) {
    if (!ep_out) return false;
    xfer_done = false;
    tuh_xfer_t xfer = {
        .daddr       = dev_addr,
        .ep_addr     = ep_out,
        .buflen      = len,
        .buffer      = (uint8_t *)data,
        .complete_cb = xfer_cb,
        .user_data   = 0
    };
    if (!tuh_edpt_xfer(&xfer)) {
        printf("[host] tuh_edpt_xfer OUT rifiutata\n");
        return false;
    }
    return wait_xfer(timeout_ms);
}

bool rcm_bulk_in(void *data, uint32_t len, uint32_t timeout_ms) {
    if (!ep_in) return false;
    xfer_done = false;
    tuh_xfer_t xfer = {
        .daddr       = dev_addr,
        .ep_addr     = ep_in,
        .buflen      = len,
        .buffer      = (uint8_t *)data,
        .complete_cb = xfer_cb,
        .user_data   = 0
    };
    if (!tuh_edpt_xfer(&xfer)) {
        printf("[host] tuh_edpt_xfer IN rifiutata\n");
        return false;
    }
    return wait_xfer(timeout_ms);
}

/*
 * Control transfer usata come trigger finale, SINCRONA.
 *
 * ATTENZIONE al callback: in TinyUSB complete_cb == NULL NON significa
 * "fire and forget", significa trasferimento BLOCCANTE su un semaforo
 * OSAL che qui non verrebbe mai segnalato, perche' nessun altro contesto
 * chiama tuh_task(): con NULL il firmware si piantava. Serve un callback
 * non nullo, e l'attesa la si fa a mano pompando tuh_task() - lo stesso
 * schema di wait_xfer per i bulk.
 *
 * Non decide cosa sia un errore: riporta l'esito e basta. Per il trigger
 * RCM un timeout e' l'esito normale di un'iniezione riuscita, e quella
 * politica sta in rcm_proto.c, non qui.
 */
rcm_xfer_t rcm_control_out(uint8_t bmRequestType, uint8_t bRequest,
                           uint16_t wValue, uint16_t wIndex, uint16_t wLength,
                           uint32_t timeout_ms) {
    // static: il transfer e' asincrono e TinyUSB potrebbe leggere questi
    // buffer dopo il ritorno della funzione.
    //
    // La dimensione NON e' arbitraria: il trigger e' una IN con wLength
    // 0x7000 e TinyUSB scrive nel buffer quello che il device consegna
    // prima di piantarsi. Un buffer piu' corto della wLength piu' grande
    // che passiamo qui e' memoria corrotta a caso.
    static CFG_TUH_MEM_SECTION CFG_TUH_MEM_ALIGN uint8_t scratch[RCM_TRIGGER_WLENGTH];
    static tusb_control_request_t req;

    if (wLength > sizeof(scratch)) {
        printf("[host] trigger: wLength 0x%04x oltre il buffer (0x%x)\n",
               wLength, (unsigned)sizeof(scratch));
        return RCM_XFER_FAILED;
    }

    req = (tusb_control_request_t){
        .bmRequestType = bmRequestType,
        .bRequest      = bRequest,
        .wValue        = wValue,
        .wIndex        = wIndex,
        .wLength       = wLength
    };

    tuh_xfer_t xfer = {
        .daddr       = dev_addr,
        .ep_addr     = 0,
        .setup       = &req,
        .buffer      = scratch,
        .complete_cb = trigger_cb,     // NON NULL: vedi commento sopra
        .user_data   = 0
    };

    trigger_done   = false;
    trigger_result = XFER_RESULT_INVALID;
    printf("[host] trigger: bRequest 0x%02x wLength 0x%04x\n", bRequest, wLength);

    if (!tuh_control_xfer(&xfer)) {
        printf("[host] tuh_control_xfer rifiutata\n");
        return RCM_XFER_FAILED;
    }

    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    while (!trigger_done) {
        tuh_task();
        if (to_ms_since_boot(get_absolute_time()) - t0 > timeout_ms) {
            printf("[host] trigger: nessuna risposta in %lu ms\n",
                   (unsigned long)timeout_ms);
            return RCM_XFER_TIMEOUT;
        }
    }

    switch (trigger_result) {
    case XFER_RESULT_SUCCESS: return RCM_XFER_OK;
    case XFER_RESULT_STALLED: return RCM_XFER_STALLED;
    case XFER_RESULT_TIMEOUT: return RCM_XFER_TIMEOUT;
    default:                  return RCM_XFER_FAILED;
    }
}

// ------------------------------------------------------------- loop

void rcm_host_init(void) {
    state = H_IDLE;
    status_set(ST_HOST_WAIT);
    printf("[host] modo HOST, attendo un device (target %04x:%04x)\n",
           APX_VID, APX_PID);
    tuh_init(BOARD_TUH_RHPORT);
}

void rcm_host_task(void) {
    tuh_task();

    if (state == H_READY) {
        state = H_INJECTING;
        status_set(ST_SENDING);

        uint32_t t0 = to_ms_since_boot(get_absolute_time());
        bool ok = rcm_proto_inject();
        uint32_t dt = to_ms_since_boot(get_absolute_time()) - t0;

        printf("[host] iniezione %s in %lu ms\n",
               ok ? "completata" : "FALLITA", (unsigned long)dt);

        state = ok ? H_DONE : H_FAILED;
        status_set(ok ? ST_DONE : ST_ERROR);
    }
}