' TRUE @ constant: entercons
' var-handler @ constant: entervar

8 byte-array: num
: clear ( -- ) 8 0 do $0 i num c! loop ;
: /%16 ( n -- q r ) dup 4 rshift swap 15 and ;
: digit ( n -- chr ) dup 10 < if 48 + else 55 + then ;
: hex ( n -- ) clear 8 0 do /%16 digit 7 i - num c! ?dup 0= if unloop exit then loop ;
: .h ( n -- ) print: '16r' hex 0 num 8 type-counted ;

: separator $: emit space space ;
: xt>link ( xt -- link | 0 ) lastword begin ?dup while 2dup link>xt = if nip exit then @ repeat drop 0 ;
: xt-type ( xt -- ) dup xt>link ?dup if link-type drop else . then ;

: line ( addr -- ) dup .h separator @ xt-type cr ;
: endword? ( addr -- bool ) @ ['] <exit> = ;
: header ( xt -- ) .h separator println: '<entercol>' ;
: body ( xt -- ) begin cell + dup line dup endword? until drop ;
: colon ( xt -- ) dup header body ;

: header ( xt -- ) dup .h separator print: '<enterdoes> dataptr: ' 2 cells + .h cr ;
: does ( xt -- ) dup header println: 'behavior:' cell + @ ( behaviorptr ) cell - body ;

: body ( xt -- ) dup .h separator @ .h cr ;
: header ( xt -- ) .h separator println: '<entercons>' ;
: cons ( xt -- ) dup header cell + body ;

: header ( xt -- ) .h separator println: '<entervar>' ;
: var ( xt -- ) dup header cell + body ;

: dump ( addr cells -- ) 0 do dup body cell + loop drop println: '...' ;

: decompile: ( "word" -- )
    ' dup @ case
        entercol  of colon endof
        enterdoes of does  endof
        entercons of cons  endof
        entervar  of var   endof
        drop ( codeword ) println: 'primitive:' @ 8 dump
    endcase ;
