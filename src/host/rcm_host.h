#ifndef RCM_HOST_H
#define RCM_HOST_H
#include <stdbool.h>
#include <stdint.h>

void rcm_host_init(void);
void rcm_host_task(void);

// Trasferimenti bulk sincroni verso il device montato.
// Ritornano false su timeout o stallo.
bool rcm_bulk_out(const void *data, uint32_t len, uint32_t timeout_ms);
bool rcm_bulk_in (void *data, uint32_t len, uint32_t timeout_ms);
/*
 * Esito di una control transfer. Sono quattro casi distinti e NON vanno
 * appiattiti su un bool a questo livello: per il trigger RCM un timeout
 * e' l'esito normale di un'iniezione riuscita, mentre uno stall e' il
 * fallimento vero. Chi chiama decide cosa considerare errore; il livello
 * di trasporto riporta solo quello che ha visto.
 */
typedef enum {
    RCM_XFER_OK = 0,      // completata, status stage chiuso
    RCM_XFER_TIMEOUT,     // nessuna risposta entro il timeout
    RCM_XFER_STALLED,     // il device ha respinto la richiesta
    RCM_XFER_FAILED,      // non e' nemmeno partita, o errore del driver
} rcm_xfer_t;

const char *rcm_xfer_name(rcm_xfer_t r);

// Control transfer sincrona: aspetta fino a timeout_ms pompando tuh_task().
rcm_xfer_t rcm_control_out(uint8_t bmRequestType, uint8_t bRequest,
                           uint16_t wValue, uint16_t wIndex, uint16_t wLength,
                           uint32_t timeout_ms);

uint8_t rcm_dev_addr(void);

#endif