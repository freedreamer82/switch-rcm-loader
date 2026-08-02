#ifndef FS_SETUP_H
#define FS_SETUP_H
#include <stdbool.h>

// Mounts to check; creates the FAT if it is not valid. Call it at boot,
// BEFORE tud_init().
bool fs_ensure_formatted(void);

#endif
