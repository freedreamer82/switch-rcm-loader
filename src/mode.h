#ifndef MODE_H
#define MODE_H
#include <stdbool.h>

typedef enum { MODE_DEVICE = 0, MODE_HOST = 1 } run_mode_t;

// Reads the mode pin, debounced. Call it exactly once at boot: switching
// role at runtime is not supported (there is only one USB controller).
run_mode_t mode_read(void);

#endif
