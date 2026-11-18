<p align="center">
  <img src="docs/logo.png" width="760"
       alt="pico-rcm - Fusee Gelee payload injector on a Raspberry Pi Pico">
</p>

<p align="center">
  <a href="https://www.paypal.me/marcogarzola"><img src="https://img.shields.io/badge/Donate-PayPal-00457C?logo=paypal&logoColor=white" alt="Donate with PayPal"></a>
</p>

# pico-rcm

An RCM payload injector for the Nintendo Switch, running on a Raspberry Pi
Pico. It is two devices in one binary:

- **DEVICE mode** — the Pico appears as a small USB drive. You drop a payload
  file on it. That is the entire configuration interface.
- **HOST mode** — the Pico becomes a USB host, waits for a Tegra bootrom to
  appear, and sends the payload the moment it does.

No PC, no app, no cable swapping at the critical moment. You load the payload
once at your desk, then in the field the Pico is a dongle you plug in.

The firmware contains no payload of its own and does not download one. You
supply the file.

---

## Scope, and what this is not

Written as a study of two things: the Tegra recovery-mode protocol, and
TinyUSB's dual-role stack on the RP2040. It is published for reference and for
people who want to read how it works. Everything below is a statement of
intent and of fact about the contents of this repository — it is not legal
advice, and what is lawful depends on where you are.

**Nothing of Nintendo's is here.** No bootrom dump, no keys, no console
firmware, no game data, no decryption of anything. Nor any payload binary —
not hekate, not Atmosphère, not a stub. `payload.bin` is a file *you* put on
the drive, from wherever you got it. What this repository contains is a USB
stack, a FAT12 volume in flash, and a 680-byte protocol header.

**The vulnerability is public and old.** Fusée Gelée is CVE-2018-6242,
disclosed by Kate Temkin and ReSwitched in 2018 and documented publicly ever
since. This is an implementation of a published protocol on a €4
microcontroller. It discloses nothing that was not already described in
detail, and it defeats no protection that is still supported: the hole was
closed in hardware years ago, which is why this only works on unpatched Erista
units and cannot be made to work on anything newer.

**On hardware you own.** The point of RCM injection here is to run your own
code, and to recover a console you have made unbootable. Nothing else.

**Not for piracy.** Nothing here circumvents copy protection, decrypts
content, or helps run software you have not paid for. If that is what you
wanted, this is the wrong project — and in most jurisdictions the wrong idea.

**The consequences are yours.** Injecting a payload voids the warranty, can
get the console and the account attached to it permanently banned from
Nintendo's online services, and can leave the unit unbootable. Feeding a
console an arbitrary binary over USB is exactly as dangerous as it sounds.
Read what your payload does before you send it.

**No affiliation.** Nintendo, Nintendo Switch, Joy-Con and Tegra are
trademarks of their respective owners, used here only to say which hardware
this talks to. This project is not affiliated with, authorised by, sponsored
by or endorsed by Nintendo Co., Ltd. or NVIDIA.

**No warranty.** Provided as is. If it bricks your console, your Pico, or your
afternoon, that is on you.

---

## Hardware it works on

This works only on Switch units whose bootrom is vulnerable to Fusée Gelée —
unpatched Erista hardware. Patched units and Mariko simply will not respond,
and the Pico will sit there blinking "waiting". There is nothing to configure
for that case: it either enumerates as an APX device or it does not.

---

## The payload file

**The file must be named `payload.bin`, in the root of the drive.**

That name is not a suggestion, it is a literal string compiled into the
firmware ([`PAYLOAD_FILENAME` in src/config.h](src/config.h#L28)). The
filesystem is FAT12 with long filenames disabled, so:

| | |
|---|---|
| Name | `payload.bin` — 8.3 format, nothing else is looked at |
| Location | root directory, **not** a subfolder |
| Case | irrelevant, in both directions — see below |
| Max size | **131056 bytes (0x1FFF0)** — see [Why 128 KB](#why-128-kb) |

So if you downloaded `hekate_ctcaer_6.2.0.bin`, **rename it**. A name that
does not fit 8.3 gets stored with a mangled short name like `HEKATE~1.BIN`,
and the firmware will not find it. The symptom is the error LED with
`[rcm] payload.bin not found` on the serial log.

Case is the one thing you do not have to think about. FAT stores short
directory entries uppercase, and FatFs uppercases the name it searches for
before comparing (the non-LFN branch of `create_name()` in `ff.c`). So
`payload.bin` and `PAYLOAD.BIN` are the same file to both sides — it does not
matter how your OS wrote it, nor which form is compiled into the firmware.
What matters is that the name fits 8.3, because that is what decides whether
a usable short entry exists at all.

### What if I put two files on it?

Nothing breaks, but only `payload.bin` is ever read. Every other file is
ignored — it just sits there consuming space. There is no menu, no ordering,
no "first file wins": the firmware opens one hardcoded name and that is it.

So to keep several payloads around, the workflow is to rename the one you
want to `payload.bin`:

```
payload.bin     <- the one that will be injected
HEKATE.BAK      <- ignored
LINUX.BAK       <- ignored
```

Two practical limits if you do that:

- The partition is **1 MB**, plenty for a handful of payloads.
- The root directory has room for **32 entries**
  ([`n_root` in fs_setup.c](src/storage/fs_setup.c#L31)), and the volume
  label uses one. Subdirectories are fine for storage — just remember the
  injected file has to be in the root.

### Copy, then wait for the LED

Writes are cached in RAM and committed to flash 750 ms after the bus goes
quiet ([`FLUSH_IDLE_MS`](src/config.h#L25)). The LED flickers fast while a
write is pending and returns to a slow pulse once it is safe.

**Eject the drive, or at least wait for the slow pulse, before unplugging.**
Pulling the cable mid-flicker loses the file. The commit cannot happen inside
the USB callback — erasing a flash sector blocks ~40 ms with interrupts off,
which would strangle the USB ISR — so it is deferred to the main loop, and
that is why the delay exists.

---

## Wiring

### Mode jumper

`MODE_PIN` is **GPIO14**, which is **physical pin 19**. The GND next to it is
**physical pin 18**. Solder a 3-pin header across **18-19-20** and one jumper
cap selects the role, with somewhere to live in either position:

```
        HOST  —  inject                DEVICE  —  USB drive

   pin 18  GND   ──┐                pin 18  GND
   pin 19  GP14  ──┘                pin 19  GP14  ──┐
   pin 20  GP15                     pin 20  GP15  ──┘

   cap on 18-19:                    cap on 19-20:
   GP14 shorted to GND, reads 0     GP14 on its pull-up, reads 1
```

So **DEVICE mode is the cap parked across 19-20** — not the cap removed. Both
work, because pin 20 is GP15 and nothing is connected to it, but parking it is
the point of the third pin: the cap never comes off the board and cannot be
lost. Taking it off entirely gives DEVICE mode too.

The printed lid says which is which, marked beside the window.

Parking is only harmless because the firmware pulls **GP15 up** as well
(`MODE_PARK_PIN`). A GPIO nobody touches keeps its reset state, and on RP2040
that is `PADS_BANK0` with `PDE=1` — a 50k pull-*down*. Left like that, the cap
parked on 19-20 would put GP14's 50k pull-up in series with it and hand the
input roughly half of VDD, which is neither a one nor a zero: the board might
come up in HOST mode with nothing plugged into it. With both pins pulled up,
parking the cap really is an open circuit.

The default is fail-safe: **anything other than a solid short to GND on pin 19
means DEVICE mode** — parked, removed, half-seated, corroded. Forget the jumper
and the result is "sent nothing", not "sent a payload into an unknown device".
The pin is sampled 16 times and needs 14 agreeing reads
([mode.c](src/mode.c#L17)), because a half-inserted or oxidised jumper is
exactly the failure you do not want to get wrong.

The role is chosen once at boot and never changes — there is only one USB
controller.

### Data

```
Pico                          Switch
────                          ──────
USB port  ───────────────────  USB-C
```

In HOST mode the Pico's USB port belongs to the target. That is the whole
port: you cannot also use it for power.

### Power

Being the USB *host* does not make the Pico the power *source* — on USB-C the
data role and the power role are independent. The Pico could not source VBUS
anyway: pin 40 is wired straight to the micro-USB connector as an **input**,
through the on-board Schottky D1 to VSYS, and the RP2040 has no VBUS switch.
And the Switch does not need it: it is self-powered.

So the only question is what powers the Pico:

- **From the target**, if its port supplies 5 V over the cable — plug in and
  look for the three boot flashes;
- **From a power bank**, otherwise. Cut a USB cable and use two wires:

| wire | Pico pin |
|---|---|
| red (+5 V) | **39** (VSYS) |
| black (GND) | **38** (GND) |

Do **not** feed 5 V into pin 40 (VBUS): it is the micro-USB connector's VBUS,
so an external supply there fights whatever is on the other end of the cable.
VSYS sits behind D1, which conducts VBUS→VSYS only, so nothing is back-fed
into the connector and no extra diode is needed. VSYS accepts 1.8–5.5 V.

You also need the target's RCM jack pin shorted, the usual way. That part is
outside the scope of this firmware.

---

## Using it

**1. Load the payload.** Jumper open, plug the Pico into a PC. A drive named
`PICORCM` appears. Copy your payload as `payload.bin`. Eject.

**2. Move the jumper** from 19-20 to **18-19** (HOST).

**3. Put the Switch in RCM** and plug in the Pico. Injection starts by itself
the moment the bootrom enumerates — there is no button. The trigger is the
appearance of a device with VID:PID `0955:7321`, and the VID/PID filter is the
only thing standing between your payload and some random USB stick.

**4. After a successful injection the Pico does not re-arm.** It stays in the
"done" pattern so it cannot fire twice. Power-cycle it for another go. A
*failed* attempt does re-arm on unplug.

---

## LED patterns

The LED is the whole interface — powered from a phone or a power bank there is
no serial console, and the USB port belongs to the target.

In DEVICE mode it always blinks. In HOST mode **on means armed, off means the
payload went out, blinking means trouble** — with the target in your hand the
only thing you need to read at a glance is "the light went out, it's done".

| Pattern | Meaning |
|---|---|
| 3 quick flashes at power-on | firmware is running, before any USB |
| blinking, 1 Hz | DEVICE mode, drive is mountable and idle |
| blinking, 5 Hz | DEVICE mode, writing — **do not unplug** |
| solid on | HOST mode, armed and waiting for the target |
| **off** | HOST mode, payload sent |
| blinking, ~1.7 Hz | HOST mode, a device is attached but its VID/PID is not APX — ignored |
| N flashes, pause, repeat | error class N, see below |

### Error codes

On failure the LED blinks out the cause: **N flashes of 200 ms, then a
one-second gap**, forever. Count the flashes.

| N | Meaning | What to do |
|---|---|---|
| 1 | the filesystem or `payload.bin` | re-copy the payload in DEVICE mode |
| 2 | the target is not talking | check the cable, that RCM is really engaged, re-seat |
| 3 | the console refused the trigger | everything worked; the bootROM is probably patched |
| 4 | internal state that should not happen | report it |

Only four on purpose. Past five or six flashes nobody counts reliably, and
the LED's job is to tell you what to **do**, not which line returned false.
The precise reason is always printed on the UART, which is where detail
belongs.

Note that **3 is not the same kind of failure as the others**: everything
worked up to the last request and the target refused it. A *timeout* on that
same request is not an error at all — it is the normal outcome of a
successful injection, and it gives you "off", not a blink.

Class **2 has a trap behind it worth knowing.** Every non-control transfer in
this firmware goes through `tuh_edpt_xfer()` with our own completion
callback, and TinyUSB compiles that entire path out unless
`CFG_TUH_API_EDPT_XFER` is 1 — which is *not* the default. With it at 0 the
transfer physically happens, the data lands in the endpoint buffer, the bus
reports no error, and the stack never tells you. It looks precisely like a
target that will not answer, while control transfers keep working throughout
because those take a different branch. It is set in
[tusb_config.h](tusb_config.h); do not remove it.

---

## What actually happens on the wire

The exploit is Fusée Gelée (public since April 2018). The firmware builds one
RCM message whose declared length is larger than the buffer that receives it,
so the copy overruns the bootrom's stack.

Layout of the message body once it lands in the target's IRAM:

```
0x40010000  ┌─────────────────────────────┐
            │  0x4001F000 repeated        │  0xF000 bytes of stack spray:
            │  0x3C00 times               │  whatever return address gets
            │                             │  smashed, it jumps to intermezzo
0x4001F000  ├─────────────────────────────┤
            │  intermezzo (92 bytes)      │  copies the payload down and
            │  + padding to 0x1000        │  jumps into it
0x40020000  ├─────────────────────────────┤
            │  your payload.bin           │
            └─────────────────────────────┘
```

Ahead of all that go 680 bytes of header, of which only the first four matter:
the declared length, `0x30298`. Then a `GET_STATUS` control request with
`wLength = 0x7000` triggers the overrun.

Two details in the implementation are worth knowing, because both are easy to
get wrong and neither fails loudly:

**The message is a byte stream, not a sequence of aligned blocks.** The header
is 680 bytes (0x2A8), so everything after it straddles the 0x1000 USB packet
boundaries. Padding the header out to a full packet shifts the whole memory
map and the injection quietly does nothing. This is why
[rcm_proto.c](src/host/rcm_proto.c) writes through a byte-level buffer and
flushes full packets, rather than sending each piece as its own transfer.

**The payload is never held in RAM.** The Pico has 264 KB. FatFs reads the
file in small pieces which are appended to the outgoing packet, so payload
size does not affect memory use at all.

Constants come from `fusee-launcher.py` (Katherine Temkin / ReSwitched); the
Fusée Gelée paper documents why it works.
They are collected at the top of [rcm_proto.h](src/host/rcm_proto.h) with the
memory map spelled out, and four `_Static_assert`s fail the build if the
arithmetic stops adding up.

### Why 128 KB

The payload lands at `0x40020000` and Tegra X1 IRAM ends at `0x40040000`.
That is `0x20000` of space, and `RCM_PAYLOAD_MAX` is 16 bytes under it. A
larger payload cannot work on any unit, so the firmware rejects it before
sending anything instead of letting it turn into a stalled bulk transfer
halfway through.

The same number falls out of a completely different route — keeping the bytes
actually sent close to the declared `0x30298` — which is a good sign it is the
right number.

### About the trigger result

Once the trigger lands, the target is already executing your payload and has
no reason to close the control transfer. **A timeout there is the normal
outcome of a successful injection**, so the firmware does not treat it as a
failure — otherwise the error LED would come on precisely when everything
worked, and the LED is all you have in the field.

A *stall* is different: it means the device rejected the request and the
overrun never happened. That is a real failure and it is reported as one.
[rcm_host.c](src/host/rcm_host.c) reports the four outcomes separately rather
than flattening them to a boolean, and [rcm_proto.c](src/host/rcm_proto.c)
decides which ones count as errors.

The only definitive verdict is still the target's screen.

---

## Building

The only thing you need is the **Pico SDK 2.3.0**. Nothing else to fetch:

- **FatFs** is vendored in [lib/fatfs/](lib/fatfs/), already configured.
- **TinyUSB** ships with the Pico SDK — both the device and the host stack.

```sh
cmake -B build -G Ninja
ninja -C build
```

Two things about `ffconf.h` if you ever update FatFs. It must be the one from
the package you extracted, because `ff.h` checks `FFCONF_DEF` against its own
release and rejects a config file from a different one. And it must stay in
`lib/fatfs/source/` — a copy in the project root wins on the include path and
gives you `#error Wrong configuration file`. CMake fails the configure step
with an explanation in both cases.

`FF_USE_LFN` is **0**, so filenames are 8.3 only. `payload.bin` fits; a long
name simply cannot be opened.

Output is `build/pico_rcm.uf2`. Hold BOOTSEL, plug in, drop the file on the
`RPI-RP2` drive.

### Build options

`FORCE_ROLE` pins the USB role at compile time instead of reading the jumper:

```sh
cmake -B build -DFORCE_ROLE=host      # inject only
cmake -B build -DFORCE_ROLE=device    # USB drive only
cmake -B build -DFORCE_ROLE=          # default: jumper decides at boot
```

Useful as a fallback if dual-role does not link, or for testing one half
without touching the wiring.

### Serial log

USB stdio is impossible — the port belongs to the target or to the PC. Logging
goes to **UART on GPIO0 (TX) / GPIO1 (RX), 115200**. In the field you will not
have it; during development it is the only window.

### Size budget

`./analyze.sh` reports flash and RAM against the real ceilings, reading
`FS_FLASH_OFFSET` from `src/config.h` rather than hardcoding it. It also
checks that `commit_sector` really ended up in SRAM — `__not_in_flash_func`
does not imply `noinline`, so `-O3` can inline it into a flash-resident caller
and silently throw the placement away. There is no build error for that, only
a device that hangs when it writes to flash.

---

## Flash layout

```
0x000000 ┌──────────────────┐
         │  firmware        │  1 MB
0x100000 ├──────────────────┤
         │  FAT12 partition │  1 MB   <- the drive you see over USB
0x200000 └──────────────────┘
```

Both halves are set by `FS_FLASH_OFFSET` and `FS_FLASH_SIZE` in
[src/config.h](src/config.h#L17). On a Pico with different flash, those two
lines are all you change.

The firmware growing past `0x100000` would corrupt the filesystem with no
error message, which is what `analyze.sh` watches for.

The partition is formatted automatically on first boot, or if the FAT is
found unreadable — FAT12, single FAT copy, 4 KB clusters matched to the flash
erase sector. FatFs and the MSC device are never active at the same time by
construction: formatting runs once before `tud_init()`, so concurrent access
to the FAT is not a problem this project has to solve.

---

## Credits and provenance

- **Fusée Gelée** was found and disclosed by Kate Temkin and ReSwitched in
  2018 (CVE-2018-6242). The protocol this firmware speaks is theirs; the
  reference implementations that came out of that work are what the header
  layout here was checked against.
- The **enclosure** is a remix of [Raspberry Pi Pico Case (1 & 2, Wireless)](https://www.printables.com/model/1368704)
  by nmattia, released CC0. Details in [case/README.md](case/README.md).
- The **jig profile** in `case/build.py` is measured off a printed Joy-Con RCM
  jig. Dimensions only — no third-party model is included.
- **A large part of this code, and of this documentation, was written with the
  help of an AI coding assistant.** It is worth knowing when you read it: the
  reasoning in the comments is real reasoning about real measurements, but it
  was not all arrived at by a human at a bench. What *was* done at the bench is
  the testing — every claim about behaviour here was checked against hardware
  or against a numeric check that is in the repository and that you can run.
  Where a claim rests on neither, it says so.

---

## Layout of the source

```
src/
  main.c              role selection at boot, the two main loops
  mode.c              reads the jumper (debounced)
  status.c            LED patterns
  usb_descriptors.c   MSC descriptors
  host/
    rcm_host.c        enumeration, VID/PID filter, USB transfers
    rcm_proto.c       builds and streams the RCM message
    rcm_proto.h       protocol constants + memory map
  storage/
    flash_fat.c       block device over internal flash, 4 KB write cache
    diskio_flash.c    FatFs glue
    msc_device.c      USB mass storage callbacks
    fs_setup.c        first-boot format
case/
  base.stl            printable enclosure, see case/README.md
  lid.stl
  build.py            builds both from the donor model, checks them, and
                      draws the section and the previews
```

---

## Support

If this project saved you some time, you can buy me a coffee ☕

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-00457C?logo=paypal&logoColor=white)](https://www.paypal.me/marcogarzola)
