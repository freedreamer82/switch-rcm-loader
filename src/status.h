#ifndef STATUS_H
#define STATUS_H

// Il LED e' l'unica interfaccia: alimentato da telefono o power bank non
// hai console seriale. Ogni stato ha un pattern distinguibile a occhio.
typedef enum {
    ST_BOOT,          // 3 lampi rapidi all'avvio
    ST_MSC_IDLE,      // respiro lento: drive montabile
    ST_MSC_BUSY,      // sfarfallio: scrittura in corso, non staccare
    ST_HOST_WAIT,     // singolo lampo al secondo: attendo un device
    ST_HOST_WRONG,    // doppio lampo: device presente ma VID/PID non APX
    ST_SENDING,       // acceso fisso
    ST_DONE,          // acceso fisso lungo + spento breve
    ST_ERROR          // SOS: lampi veloci continui
} status_t;

void status_init(void);
void status_set(status_t s);
void status_task(void);   // non bloccante, chiamala nel loop principale

#endif
