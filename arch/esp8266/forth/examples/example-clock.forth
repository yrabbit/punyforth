NTP load
SSD1306I2C load
FONT57 load

variable: time
variable: tick
0 init-variable: last-sync
3 byte-array: ]mm   0 2 ]mm c!  : mm 0 ]mm ;
3 byte-array: ]hh   0 2 ]hh c!  : hh 0 ]hh ;

: fetch 123 "time.google.com" network-time ;
: sync { fetch time ! ms@ last-sync ! } catch ?dup if print: 'sync error:' ex-type cr then ;
: age ms@ last-sync @ - ;
: expired? age 60000 15 * > ;
: stale? age 60000 60 * > ;
: time@ expired? if sync time @ else time @ age 1000 / + then ;
: mins time@ 60 / 60 % ;
: hour time@ 3600 / 24 % ;
: secs time@ 60 % ;

: format
    hour 10 < if $0 hh c! 1 else 0 then ]hh hour >str
    mins 10 < if $0 mm c! 1 else 0 then ]mm mins >str ;

: centery HEIGHT 2 / 4 - text-top ! ;
: colon tick @ if ":" else " " then draw-str tick @ invert tick ! ;
: draw-time
    0 fill-buffer
    0 text-left ! centery
    hh draw-str colon mm draw-str ;

: draw format draw-time display ;
: start ( task -- ) activate begin draw 1000 ms pause again ;

0 task: time-task
: main
    display-init font5x7 font !  
    sync multi time-task start ;

main
