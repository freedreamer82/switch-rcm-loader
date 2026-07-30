#ifndef MODE_H
#define MODE_H
#include <stdbool.h>

typedef enum { MODE_DEVICE = 0, MODE_HOST = 1 } run_mode_t;

// Legge il pin di modo con debounce. Da chiamare una volta sola al boot:
// cambiare modo a runtime non e' supportato (un solo controller USB).
run_mode_t mode_read(void);

#endif
