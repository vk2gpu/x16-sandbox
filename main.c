#include <stdint.h>
#include <stdio.h>
#include <conio.h>
#include <6502.h>
#include <cx16.h>

#include "sine_tab.h"
#include "palette.h"
#include "tilemap.h"

#define MAP_BASE        0x00000
#define TILE_BASE       0x10000

#define VREG_CMP        0xF0000
#define VREG_PAL        0xF1000
#define VREG_LAY1       0xF2000
#define VREG_LAY2       0xF3000
#define VREG_SPR        0xF4000
#define VREG_SPRD       0xF5000

#define VERA_AUTO_INC_1 0x100000

#define KERNAL_ISR (*(void**)0x0314)
static void* KERNAL_ISR_HANDLER;

#define BEGIN_ISR()                                 \
    __asm__ ("sei");                                \
    __asm__ ("pha");                                \
    __asm__ ("phx");                                \
    __asm__ ("phy")

#define END_ISR()                                   \
    __asm__ ("ply");                                \
    __asm__ ("plx");                                \
    __asm__ ("pla");                                \
    __asm__ ("ply");                                \
    __asm__ ("plx");                                \
    __asm__ ("pla");                                \
    __asm__ ("rti")

#define NEXT_ISR()                                  \
    __asm__ ("ply");                                \
    __asm__ ("plx");                                \
    __asm__ ("pla");                                \
    __asm__ ("jmp (_KERNAL_ISR_HANDLER)")

#define vera_vset(addr) VERA.address = (addr) & 0xffff; VERA.address_hi = (((addr) | VERA_AUTO_INC_1) >> 16)

#define vera_write8(data) VERA.data0 = data

#define vera_write16(data) VERA.data0 = data & 0xff; VERA.data0 = data >> 8;

static void vera_write(const uint8_t* src, uint16_t num)
{
    uint16_t i = 0;
    for(; i < num; ++i)
        VERA.data0 = src[i];
}

static void vera_set_irq(void* irqFn)
{
    KERNAL_ISR_HANDLER = KERNAL_ISR;
    SEI();
    VERA.irq_enable = 0;
    KERNAL_ISR = irqFn;
    VERA.irq_enable = VERA_IRQ_VSYNC | VERA_IRQ_RASTER;
    CLI();
}

#define vera_set_next_irq(scanline) vera_vset(VREG_CMP + 9); vera_write16(scanline)


static void vera_init()
{
    uint16_t i = 0;

    // Disable layer 2.
    vera_vset(VREG_LAY2);
    vera_write8(0);

    // Setup layer 1.
    vera_vset(VREG_LAY1);
    // mode=4, enabled=1
    vera_write8((4 << 5) | 1);
    // tileh=0, tilew=0, maph=1(32), mapw=2(64)
    vera_write8((1 << 5) | (1 << 4) | (0 << 2) | (1 << 0));
    // map_base
    vera_write16(MAP_BASE >> 2);
    // tile_base
    vera_write16(TILE_BASE >> 2);

    // Upload palette.
    vera_vset(VREG_PAL);
    vera_write((const uint8_t*)PALETTE, sizeof(PALETTE));

    // Upload tile map.
    vera_vset(MAP_BASE);
    vera_write((const uint8_t*)MAP_DATA, sizeof(MAP_DATA));
    vera_vset(TILE_BASE);
    vera_write((const uint8_t*)TILE_DATA, sizeof(TILE_DATA));
}



static volatile uint16_t nextScanline = 0;
static volatile uint8_t frameCounter = 0;
static uint8_t offsetTemp = 0;
static uint8_t hscrollTab[256];
void __fastcall__ vera_isr()
{
    BEGIN_ISR();

    if(VERA.irq_flags & VERA_IRQ_RASTER)
    {
        VERA.irq_flags = VERA_IRQ_RASTER;

        offsetTemp = hscrollTab[(uint8_t)nextScanline];

        // Set scroll.
        vera_vset(VREG_LAY1 + 6);
        vera_write16((int16_t)offsetTemp - 127);

        nextScanline += 1;
        if(nextScanline >= 0x1E0)
        {
            nextScanline = 0;
            frameCounter++;

        }

        vera_set_next_irq(nextScanline);
 
        END_ISR();
    }

    NEXT_ISR();
}

static volatile uint8_t lastFrameCount = 0;
int main()
{
    uint16_t i;
    uint16_t sine_tab;

    vera_init();
    vera_set_next_irq(0);
    vera_set_irq(vera_isr);

    for(;;)
    {
        for(i = 0; i < 256; ++i)
        {
            sine_tab = ((i >> 3) * 256);
            hscrollTab[i] = SINE_TAB[sine_tab + ((i >> 1) + (frameCounter << 1) & 0xff)];
        }

        while(lastFrameCount == frameCounter) CLI();
        lastFrameCount = frameCounter;
    }

    return 0;
}
