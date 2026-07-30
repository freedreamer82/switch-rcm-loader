#!/usr/bin/env bash
#
# size.sh — flash and RAM budget report for the pico-rcm firmware
#
# Reads FS_FLASH_OFFSET from src/config.h rather than hardcoding it, so
# the report stays truthful if you change the flash layout.
#
# usage:  ./tools/size.sh [file.elf]
#         TC=/other/path/bin ./tools/size.sh
#
set -uo pipefail

# Force C locale. Under it_IT (and any comma-decimal locale) awk emits
# "55,0" while bash printf demands "55.0", and the script dies on its
# own output.
export LC_ALL=C

ELF="${1:-build/pico_rcm.elf}"
TC="${TC:-$HOME/.pico-sdk/toolchain/15_2_Rel1/bin}"
CONFIG="${CONFIG:-src/config.h}"
RAM_TOTAL=$((264 * 1024))          # RP2040

SIZE="$TC/arm-none-eabi-size"
NM="$TC/arm-none-eabi-nm"
OBJDUMP="$TC/arm-none-eabi-objdump"

die() { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

[[ -f "$ELF" ]]  || die "ELF not found: $ELF   (did you build?)"
[[ -x "$SIZE" ]] || die "toolchain not found in $TC
      point TC at the right directory:  TC=~/.pico-sdk/toolchain/<ver>/bin $0"

# ------------------------------------------------------ read config.h
# Accepts both  1048576  and  (1024u * 1024u)
# Evaluated with bash arithmetic rather than bc, which is not installed
# everywhere. The guard keeps $(( )) away from anything but arithmetic.
FS_EXPR=$(
    if [[ -f "$CONFIG" ]]; then
        sed -n 's/.*#define[[:space:]]\+FS_FLASH_OFFSET[[:space:]]\+\(.*\)/\1/p' "$CONFIG" \
        | head -1 | sed 's|//.*||; s|/\*.*||' | tr -d 'uU' | tr -d '[:space:]'
    fi
)
FS_OFFSET=""
if [[ -n "${FS_EXPR:-}" && "$FS_EXPR" =~ ^[0-9x*+()\<-]+$ ]]; then
    FS_OFFSET=$(( FS_EXPR )) 2>/dev/null || FS_OFFSET=""
fi
if [[ -z "${FS_OFFSET:-}" ]] || ! [[ "$FS_OFFSET" =~ ^[0-9]+$ ]] || (( FS_OFFSET == 0 )); then
    FS_OFFSET=$((1024 * 1024))
    FS_NOTE=" (default; could not parse $CONFIG)"
else
    FS_NOTE=""
fi

# ------------------------------------------------------ helpers
human() { awk -v b="$1" 'BEGIN{ if (b < 1024) printf "%d B", b; else printf "%.1f KB", b/1024 }'; }

bar() {  # bar <used> <total> [width]
    awk -v u="$1" -v t="$2" -v w="${3:-38}" 'BEGIN{
        p = (t > 0) ? u/t : 0; if (p > 1) p = 1
        n = int(p*w + 0.5)
        printf "%s", (p > 0.95) ? "\033[31m" : (p > 0.80) ? "\033[33m" : "\033[32m"
        for (i = 0; i < n; i++) printf "#"
        printf "\033[0m"
        for (i = n; i < w; i++) printf "."
        printf "  %5.1f%%", p*100
    }'
}

sec() { "$SIZE" -A "$ELF" | awk -v s="$1" '$1 == s { print $2; exit }'; }

# mawk does not understand 0x literals (it evaluates them as 0) and has
# no strtonum(), so hex is converted by hand and bounds are decimal:
#   268435456 = 0x10000000  XIP window base
#   536870912 = 0x20000000  SRAM base
HEX2DEC='function h2d(s,  i,c,n,d) {
    s = tolower(s); n = 0
    for (i = 1; i <= length(s); i++) {
        c = substr(s, i, 1)
        d = index("0123456789abcdef", c) - 1
        if (d < 0) continue
        n = n * 16 + d
    }
    return n
}'

# ------------------------------------------------------ collect
# Flash = every section whose LMA lands in the XIP window. .data belongs
# here (its initialisers live in flash) and also counts against RAM.
read -r FLASH_USED FLASH_LO FLASH_HI < <("$OBJDUMP" -h "$ELF" | awk "$HEX2DEC"'
    /^[[:space:]]*[0-9]+[[:space:]]/ {
        sz = h2d($3); lma = h2d($5)
        if (sz > 0 && lma >= 268435456 && lma < 536870912) {
            tot += sz
            if (lo == 0 || lma < lo) lo = lma
            if (lma + sz > hi) hi = lma + sz
        }
    }
    END { printf "%d %d %d\n", tot+0, lo+0, hi+0 }')

RAM_STATIC=$("$SIZE" -A "$ELF" | awk '
    $1 == ".data" || $1 == ".bss" || $1 == ".ram_vector_table" ||
    $1 == ".uninitialized_data" || $1 == ".scratch_x" || $1 == ".scratch_y" { t += $2 }
    END { print t+0 }')

HEAP=$(sec .heap);        HEAP=${HEAP:-0}
STACK=$(sec .stack_dummy); STACK=${STACK:-0}

# ------------------------------------------------------ report
printf '\n\033[1m%s\033[0m\n' "SIZE BUDGET — $(basename "$ELF")"
printf '%s\n' "================================================================"

printf '\n\033[1mFLASH\033[0m  (ceiling = start of the FAT12 partition)\n'
printf '  %-13s %10s   ' "firmware" "$(human "$FLASH_USED")"; bar "$FLASH_USED" "$FS_OFFSET"; echo
printf '  %-13s %10s%s\n' "ceiling" "$(human "$FS_OFFSET")" "$FS_NOTE"
if (( FLASH_USED >= FS_OFFSET )); then
    printf '  \033[31m%s\033[0m\n' "OVER by $(human $((FLASH_USED - FS_OFFSET)))"
    printf '  \033[31m%s\033[0m\n' "The firmware writes into the filesystem. You will not get an"
    printf '  \033[31m%s\033[0m\n' "error - you will get a FAT that corrupts itself. Raise"
    printf '  \033[31m%s\033[0m\n' "FS_FLASH_OFFSET in $CONFIG and reformat."
else
    printf '  %-13s %10s\n' "headroom" "$(human $((FS_OFFSET - FLASH_USED)))"
fi
for s in .text .rodata .boot2 .binary_info; do
    v=$(sec "$s"); [[ -n "${v:-}" && "$v" != 0 ]] && printf '    %-18s %10s\n' "$s" "$(human "$v")"
done
v=$(sec .data); [[ -n "${v:-}" ]] && printf '    %-18s %10s   also counted in RAM\n' ".data" "$(human "$v")"
printf '  span          0x%08x - 0x%08x\n' "$FLASH_LO" "$FLASH_HI"

printf '\n\033[1mRAM\033[0m    (264 KB on RP2040)\n'
printf '  %-13s %10s   ' "static" "$(human "$RAM_STATIC")"; bar "$RAM_STATIC" "$RAM_TOTAL"; echo
printf '  %-13s %10s   for stack and heap\n' "free" "$(human $((RAM_TOTAL - RAM_STATIC)))"
for s in .bss .data .ram_vector_table; do
    v=$(sec "$s"); [[ -n "${v:-}" && "$v" != 0 ]] && printf '    %-18s %10s\n' "$s" "$(human "$v")"
done
(( HEAP  )) && printf '    %-18s %10s   reserved\n' ".heap"  "$(human "$HEAP")"
(( STACK )) && printf '    %-18s %10s   reserved\n' ".stack" "$(human "$STACK")"

# ------------------------------------------------------ sanity check
# commit_sector() must execute from SRAM, and there is no build-time
# error if it does not: __not_in_flash_func does NOT imply noinline, so
# -O3 can inline it into a flash-resident caller and silently discard
# the section attribute. Note there is no separate .time_critical output
# section to look for - the linker script folds .time_critical* into
# .data - so the symbol address is the only reliable evidence.
printf '\n\033[1mSANITY\033[0m\n'
FOUND=0
while read -r addr _type name; do
    FOUND=1
    case "$addr" in
        2*) printf '  \033[32mok\033[0m    %s at 0x%s (SRAM)\n' "$name" "$addr" ;;
        1*) printf '  \033[31mFAIL\033[0m  %s at 0x%s is in FLASH\n' "$name" "$addr"
            printf '        Use __no_inline_not_in_flash_func for this function.\n' ;;
        *)  printf '  ?     %s at 0x%s - unexpected region\n' "$name" "$addr" ;;
    esac
done < <("$NM" "$ELF" 2>/dev/null | grep -w "commit_sector" || true)
if (( ! FOUND )); then
    printf '  \033[31mFAIL\033[0m  commit_sector not in the symbol table\n'
    printf '        It was inlined, which throws away the RAM placement.\n'
    printf '        Use __no_inline_not_in_flash_func in flash_fat.c.\n'
fi

# ------------------------------------------------------ symbols
printf '\n\033[1mLARGEST SYMBOLS\033[0m\n'
# Linker-script markers (__StackTop, __HeapLimit, __flash_binary_end...)
# get nonsense sizes from --size-sort because they are absolute symbols.
# Anything bigger than the whole SRAM is one of those: drop it.
"$NM" -C --size-sort -S "$ELF" 2>/dev/null | awk "$HEX2DEC"'
    NF >= 4 {
        sz = h2d($2)
        if (sz > 270336) next          # 264 KB: cannot be a real object
        if ($4 ~ /^__/) next           # linker markers
        printf "%d\t%s\t%s\n", sz, $3, $4
    }' | sort -rn | head -12 | while IFS=$'\t' read -r sz type name; do
    printf '  %10s  %s  %s\n' "$(human "$sz")" "$type" "$name"
done

# ------------------------------------------------------ per object
printf '\n\033[1mLARGEST OBJECT FILES\033[0m\n'
# Sizing the .obj files directly beats parsing the .map: the map format
# changes between SDK releases, the object files do not.
OBJS=$(find "$(dirname "$ELF")" -name '*.obj' -o -name '*.o' 2>/dev/null | head -400)
if [[ -n "$OBJS" ]]; then
    # shellcheck disable=SC2086
    "$SIZE" $OBJS 2>/dev/null | awk '
        NR > 1 && NF >= 6 {
            n = $6; sub(/.*\//, "", n)
            printf "%d\t%s\n", $1 + $2 + $3, n
        }' | sort -rn | head -12 | while IFS=$'\t' read -r sz name; do
        printf '  %10s  %s\n' "$(human "$sz")" "$name"
    done
else
    printf '  no object files found under %s\n' "$(dirname "$ELF")"
fi

printf '\n\033[2m%s\033[0m\n' "Static buffers to expect in .bss: 4 KB flash cache (flash_fat.c),
4 KB payload chunk (rcm_proto.c), 4 KB MSC endpoint buffer (TinyUSB),
~1 KB FatFs work area (fs_setup.c). The payload itself is streamed from
flash and never held in RAM, so its size does not appear here."