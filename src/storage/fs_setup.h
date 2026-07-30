#ifndef FS_SETUP_H
#define FS_SETUP_H
#include <stdbool.h>

// Monta per verifica; se il FAT non e' valido lo crea. Da chiamare al
// boot, PRIMA di tud_init().
bool fs_ensure_formatted(void);

#endif
