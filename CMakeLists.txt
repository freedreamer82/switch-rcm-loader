# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.3.0)
set(toolchainVersion 15_2_Rel1)
set(picotoolVersion 2.3.0)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

# Il nome del progetto DEVE combaciare col nome del target add_executable
# (pico_rcm): l'estensione VS Code ricava il binario da flashare con la regex
# /project\(([^)\s]+)/ e cerca build/<nome>.elf . Se i due nomi divergono,
# "Run Project" passa a picotool un path che non esiste.
project(pico_rcm C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# # Add executable. Default name is the project name, version 0.1

# add_executable(switch-rpm-loader switch-rpm-loader.c )

# pico_set_program_name(switch-rpm-loader "switch-rpm-loader")
# pico_set_program_version(switch-rpm-loader "0.1")

# # Modify the below lines to enable/disable output over UART/USB
# pico_enable_stdio_uart(switch-rpm-loader 0)
# pico_enable_stdio_usb(switch-rpm-loader 0)

# # Add the standard library to the build
# target_link_libraries(switch-rpm-loader
#         pico_stdlib)

# # Add the standard include files to the build
# target_include_directories(switch-rpm-loader PRIVATE
#         ${CMAKE_CURRENT_LIST_DIR}
# )

# pico_add_extra_outputs(switch-rpm-loader)



# ===================================================================
#  pico-rcm — incolla TUTTO questo blocco nel CMakeLists.txt generato
#  dall'estensione, SOTTO la riga  pico_sdk_init()  , cancellando
#  quello che l'estensione aveva messo dopo (add_executable, ecc).
#
#  NON toccare le righe sopra: contengono la magia dei percorsi SDK
#  dell'estensione, e sono specifiche della tua installazione.
# ===================================================================

# ------------------------------------------------------------ FatFs
set(FATFS_DIR ${CMAKE_CURRENT_LIST_DIR}/lib/fatfs/source)

if(NOT EXISTS ${FATFS_DIR}/ff.c)
    message(FATAL_ERROR
        "\n"
        "FatFs non trovato in lib/fatfs/source\n"
        "\n"
        "  1. scarica il pacchetto da  http://elm-chan.org/fsw/ff/\n"
        "  2. estrailo in  lib/fatfs/   (dentro deve stare  source/ff.c )\n"
        "  3. Delete Cache and Reconfigure\n")
endif()

# ffconf.h DEVE essere quello del pacchetto scaricato: ff.h confronta
# FFCONF_DEF con la propria versione e rifiuta un file di configurazione
# di un'altra release. Si modifica quello in lib/fatfs/source/, non se ne
# scrive uno nuovo. La cartella e' negli include, quindi ff.h lo trova.
if(EXISTS ${CMAKE_CURRENT_LIST_DIR}/ffconf.h)
    message(FATAL_ERROR
        "\n"
        "C'e' un ffconf.h nella cartella radice: cancellalo.\n"
        "Vince su quello del pacchetto FatFs e causa\n"
        "  #error Wrong configuration file (ffconf.h)\n")
endif()

# ------------------------------------------------------------ target
add_executable(pico_rcm
    src/main.c
    src/mode.c
    src/status.c
    src/usb_descriptors.c
    src/storage/flash_fat.c
    src/storage/diskio_flash.c
    src/storage/msc_device.c
    src/storage/fs_setup.c
    src/host/rcm_host.c
    src/host/rcm_proto.c
    ${FATFS_DIR}/ff.c
)   # ffunicode.c NON serve: lo richiede solo FF_USE_LFN != 0

# La cartella radice serve per tusb_config.h e ffconf.h: TinyUSB e FatFs
# li cercano per nome nel percorso di include, non in una sottocartella.
target_include_directories(pico_rcm PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/src
    ${FATFS_DIR}
)

# ------------------------------------------------------------ ruolo USB
# Vuoto  = un solo binario, il jumper decide al boot  <-- prova questo
# host   = solo iniezione (fallback se il dual-role non linka)
# device = solo drive USB
set(FORCE_ROLE "" CACHE STRING "vuoto | host | device")

if(FORCE_ROLE STREQUAL "host")
    target_compile_definitions(pico_rcm PRIVATE FORCE_ROLE_HOST=1)
    message(STATUS "pico-rcm: ruolo forzato HOST")
elseif(FORCE_ROLE STREQUAL "device")
    target_compile_definitions(pico_rcm PRIVATE FORCE_ROLE_DEVICE=1)
    message(STATUS "pico-rcm: ruolo forzato DEVICE")
else()
    message(STATUS "pico-rcm: dual-role (jumper a runtime)")
endif()

target_link_libraries(pico_rcm
    pico_stdlib
    hardware_flash
    hardware_sync
    tinyusb_device
    tinyusb_host
)

# Console USB impossibile: la porta serve al target o al PC.
# UART su GPIO0 (TX) / GPIO1 (RX), 115200.
pico_enable_stdio_usb(pico_rcm 0)
pico_enable_stdio_uart(pico_rcm 1)

pico_add_extra_outputs(pico_rcm)