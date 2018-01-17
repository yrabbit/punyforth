NTP load
SSD1306I2C load
FONT57 load

variable: clock
variable: tick
0 init-variable: last-sync
3 byte-array: ]mm   0 2 ]mm c!  : mm 0 ]mm ;
3 byte-array: ]hh   0 2 ]hh c!  : hh 0 ]hh ;

create: months 31 c, 28 c, 31 c, 30 c, 31 c, 30 c, 31 c, 31 c, 30 c, 31 c, 30 c, 31 c,

: age ms@ last-sync @ - ;
: expired? age 60000 15 * > ;
: stale? age 60000 60 * > ;
: fetch 123 "time.google.com" network-time ;
: sync { fetch clock ! ms@ last-sync ! } catch ?dup if print: 'sync error:' ex-type cr then ;
: utc  clock @ age 1000 / + ;
: mins utc 60 / 60 % ;
: hour utc 3600 / 24 % ;
: secs utc 60 % ;

: leapyear? dup 4 % 0= over 100 % 0<> and swap 400 % 0= or ;
\ based on: http://howardhinnant.github.io/date_algorithms.html#civil_from_days
: era   ( ts -- n ) 86400 / 719468 + dup 0< if 146096 - then 146097 / ;
: doe   ( ts -- n ) dup 86400 / 719468 + swap era 146097 * - ;
: yoe   ( ts -- n ) doe dup 1460 / over 36524 / + over 146096 / - - 365 / ;
: doy   ( ts -- n ) dup doe swap yoe dup 365 * over 4 / + swap 100 / - - ;
: mp    ( ts -- n ) doy 5 * 2 + 153 / ;

: epoch-days ( -- n ) utc era 146097 * utc doe + 719468 - ;
: weekday ( -- 0..6=sun..sat ) epoch-days dup -4 >= if 4 + 7 % else 5 + 7 % 6 + then ;
: day   ( -- 1..31 ) utc doy utc mp 153 * 2 + 5 / - 1+ ;
: month ( -- 1..12 ) utc mp dup 10 < if 3 else -9 then + ;
: year  ( -- n ) utc yoe utc era 400 * + month 2 < if 1 else 0 then + ;

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
: start ( task -- ) activate begin expired? if sync then draw 1000 ms pause again ;

0 task: time-task
: main
    display-init font5x7 font !  
    sync multi time-task start ;

main
