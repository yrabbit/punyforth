#include "FreeRTOS.h"
#include "espressif/esp_common.h"
#include "esp/uart.h"
#include "task.h"
#include "forth_io.h"

#define BUFFER_SIZE 1024 // should be multiple of 4
bool loading = false;
char *buffer = NULL;
int buffer_offset = -1;
uint32_t source_code_address;

void forth_load(uint32_t address) {
    source_code_address = address;
    loading = true;
}

void forth_end_load() {
    printf("Punyforth ready.\n");
    loading = false;
    free(buffer);
    buffer = NULL;
}

int next_char_from_flash() { // read source stored code from flash memory
    if (buffer == NULL) buffer = malloc(BUFFER_SIZE);
    if (buffer_offset < 0 || buffer_offset >= BUFFER_SIZE) {
        sdk_spi_flash_read(source_code_address, (void *) buffer, BUFFER_SIZE);
        source_code_address += BUFFER_SIZE;
        buffer_offset = 0;
    }
    return buffer[buffer_offset++];
}

int forth_getchar() { 
    return loading ? next_char_from_flash() : getchar();
}

bool _enter_press = false; // XXX this is ugly, use for breaking out key loop
void forth_push_enter() { _enter_press = true; }

int check_enter() { 
   if (_enter_press) {
       _enter_press = false;
       return 10;
   }
   return -1;
}

int forth_getchar_nowait() {
   if (loading) return next_char_from_flash();
   taskYIELD();
   char buf[1];
   return sdk_uart_rx_one_char(buf) != 0 ? check_enter() : buf[0];
}

void forth_putchar(char c) { printf("%c", c); }
void forth_type(char* text) { printf("%s", text); }
void forth_uart_set_baud(int uart_num, int bps) { uart_set_baud(uart_num, bps); }

