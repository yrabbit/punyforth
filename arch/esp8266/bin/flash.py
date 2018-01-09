import sys, os
from argparse import ArgumentParser, RawDescriptionHelpFormatter

class BlockNumber:
    @staticmethod
    def from_address(addr): return BlockNumber(addr / 4096)
    def __init__(self, num): self.num = num
    def __str__(self): return str(self.num)

class App:
    def __init__(self, path, load_addresses):
        self.path = path
        self.load_addresses = load_addresses

    def prepared(self):
        name = 'main.tmp'
        with open(name, "wt") as f:
            for each in self.load_addresses: f.write("%s load\n" % BlockNumber.from_address(each))
            f.write(self.read())
            f.write("stack-show\n")
            f.write("/end\n")
        return name

    def read(self):
        if not self.path: return ''
        with open(self.path, "rt") as app: return app.read()

class ModuleAddress:
    def __init__(self, start, increment):
        self.start = start
        self.current = start
        self.increment = increment

    def next(self):
        actual = self.current
        self.current += self.increment
        return actual

    def reset(self): self.current = self.start

class Code:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.content = self.load(path)

    def load(self, path):
        with open(path) as f: return f.read()

    def validate(self, max_size, max_line_len):
        if len(self.content) > max_size:
            raise RuntimeError('File is too large (%d), won''t fit in flash. Max size is %d' % (len(self.content), max_size))
        if any(len(line) > max_line_len for line in self.content.split('\n')):
            raise RuntimeError('Input overflow at line: "%s"' % [line for line in self.content.split('\n') if len(line) >= max_line_len][0])

    def to_block_format(self, max_line_len, output_file):
        self.save(self.pad(max_line_len), output_file)

    def pad(self, max_line_len):
        """ This is for the block screen editor. A screen = 128 columns and 32 rows """
        def pad_line(line):
            return line + (' ' * (max_line_len - len(line)))
        return '\n'.join([pad_line(line) for line in self.content.split('\n')])

    def save(self, content, output_file):
        with open(output_file, 'wt') as f: f.write(content)

class Modules:
    class All:
        def __call__(self, code): return True
        def __str__(self): return 'ALL'

    class Nothing:
        def __call__(self, code): return code.name.lower() == 'app'
        def __str__(self): return 'NONE'

    class Only:
        def __init__(self, names): 
            self.names = set(each.lower() for each in names)
            self.names.add('core')
            self.names.add('app')
            self.names.add('layout')
        def __call__(self, code): return code.name.lower() in self.names
        def __str__(self): return 'Only: %s' % self.names

    def __init__(self, start_address, layout_address, max_size, max_line_len):
        self.max_size = max_size
        self.address = ModuleAddress(start_address, max_size)
        self.layout_address = layout_address
        self.max_line_len = max_line_len
        self.modules = []
        self.module_filter = Modules.All()

    def add(self, code):
        code.validate(self.max_size, self.max_line_len)
        self.modules.append(code)
        return self

    def select(self, module_filter):
        print 'Selected modules: %s' % module_filter
        self.module_filter = module_filter
    
    def selected(self):
        return (each for each in self.modules if self.module_filter(each))

    def flash(self, esp, block_format):
        self.flash_layout(esp, block_format)
        self.flash_modules(esp, block_format)

    def flash_layout(self, esp, block_format):
        layout = Layout.generate(self.to_be_flashed())
        if self.module_filter(layout):
            self.transform_and_save(layout, self.layout_address, esp, block_format)

    def flash_modules(self, esp, block_format):
        for address, code in self.to_be_flashed():
            self.transform_and_save(code, address, esp, block_format)

    def to_be_flashed(self):
        result = []
        self.address.reset()
        for code in self.selected():
            result.append((self.address.next(), code))
        return result

    def transform_and_save(self, code, address, esp, block_format):
        print "Flashing %s" % code.name
        if block_format:
            code.to_block_format(self.max_line_len, 'block.tmp')
            self.save_to_esp(address, 'block.tmp', esp, self.max_size)
        else:
            self.save_to_esp(address, code.path, esp, self.max_size)

    def save_to_esp(self, address, path, esp, max_size):
        if os.path.getsize(path) > max_size:
            raise RuntimeError('File is too large %s' % path)
        esp.write_flash(address, path)
    
class Layout:
    @staticmethod
    def generate(flashed_modules):
        layout = 'layout.tmp'
        with open(layout, 'wt') as f:
            for address, code in flashed_modules:
                if code.name not in ['APP', 'CORE']:
                    f.write('%s constant: %s\n' % (BlockNumber.from_address(address), code.name))
            f.write('/end\n')
        return Code(layout, 'LAYOUT')

class Binaries:
    def __init__(self):
        self.binaries = (
            (0x0000, 'rboot.bin'),
            (0x1000, 'blank_config.bin'),
            (0x2000, 'punyforth.bin'))

    def flash(self, esp):
        print("Flashing binaries..")
        esp.write_flash_many(self.binaries)
    
class Esp:
    def __init__(self, port):
        self.port = port

    def write_flash(self, address, path):
        os.system("python esptool.py -p %s write_flash 0x%x %s" % (self.port, address, path))

    def write_flash_many(self, tupl):
        os.system("python esptool.py -p %s write_flash -fs 32m -fm dio -ff 40m %s" % (self.port, ' '.join("0x%x %s" % each for each in tupl)))

class CommandLine:
    @staticmethod
    def to_bool(v):
        if v.lower() in ('yes', 'true', 'y', '1'): return True
        if v.lower() in ('no', 'false', 'n', '0'): return False
        raise argparse.ArgumentTypeError('%s is not a boolean' % v)

    def __init__(self):
        self.parser = ArgumentParser(description='Flash punyforth binaries and forth code.', epilog=self.examples(), formatter_class=RawDescriptionHelpFormatter)
        self.parser.add_argument('port', help='COM port of the esp8266')
        self.parser.add_argument('--modules', nargs='*', default=['all'], help='List of modules. Default is "all".')
        self.parser.add_argument('--binary', default=True, type=CommandLine.to_bool, help='Use "no" to skip flashing binaries. Default is "yes".')
        self.parser.add_argument('--main', default='', help='Path of the Forth code that will be used as an entry point.')
        self.parser.add_argument('--block-format', default=False, type=CommandLine.to_bool, help='Use "yes" to format source code into block format (128 columns and 32 rows padded with spaces). Default is "no".')

    def examples(self):
        return """
Examples:
Flash only source code in block format. Only flash the "flash" module.
    $ python flash.py /dev/cu.wchusbserial1410 --binary false --block-format true --main myapp.forth --modules flash

Flash all modules and binaries:
    $ python flash.py /dev/cu.wchusbserial1410

Flash all modules, binaries and use myapp.forth as an entry point:
    $ python flash.py /dev/cu.wchusbserial1410 --main myapp.forth

Available modules:\n%s
        """ % '\n'.join("\t* %s" % each.name for each in AVAILABLE_MODULES)
    
    def parse(self):
        args = self.parser.parse_args()
        args.modules = self.modules(args)
        return args

    def modules(self, args):
        if args.modules == ['all']: return Modules.All()
        if args.modules == ['none']: return Modules.Nothing()
        return Modules.Only(args.modules)

START_ADDRESS   = 0x52000
LAYOUT_ADDRESS  = 0x51000
MAX_MODULE_SIZE = 49152

# TODO:
# Protection against loading multiple transitive modules
# Fix flash edit

AVAILABLE_MODULES = [
    Code("../../../generic/forth/core.forth", 'CORE'),
    Code("../forth/dht22.forth", 'DHT22'),
    Code("../forth/flash.forth", 'FLASH'),
    Code("../forth/font5x7.forth", 'FONT57'),
    Code("../forth/gpio.forth", 'GPIO'),
    Code("../forth/mailbox.forth", 'MAILBOX'),
    Code("../forth/netcon.forth", 'NETCON'),
    Code("../forth/ntp.forth", 'NTP'),
    Code("../forth/ping.forth", 'PING'),
    Code("../forth/sonoff.forth", 'SONOFF'),
    Code("../forth/ssd1306-i2c.forth", 'SSD1306I2C'),
    Code("../forth/ssd1306-spi.forth", 'SSD1306SPI'),
    Code("../forth/tasks.forth", 'TASKS'),
    Code("../forth/tcp-repl.forth", 'TCPREPL'),
    Code("../forth/turnkey.forth", 'TURNKEY'),
    Code("../forth/wifi.forth", 'WIFI'),
    Code("../forth/event.forth", 'EVENT'),
    Code("../../../generic/forth/ringbuf.forth", 'RINGBUF'),
    Code("../../../generic/forth/decompiler.forth", 'DECOMP')
]

def tmpfiles(): return (each for each in os.listdir('.') if each.endswith('.tmp'))
def remove(files):
    for each in files: os.remove(each)

if __name__ == '__main__':
    args = CommandLine().parse()
    esp = Esp(args.port)
    app = App(path=args.main, load_addresses=[START_ADDRESS + MAX_MODULE_SIZE, LAYOUT_ADDRESS])
    modules = Modules(START_ADDRESS, LAYOUT_ADDRESS, MAX_MODULE_SIZE, max_line_len=128 - len(os.linesep))
    modules.add(Code(app.prepared(), 'APP'))
    for each in AVAILABLE_MODULES: modules.add(each)
    modules.select(args.modules)
    if args.binary: Binaries().flash(esp)
    modules.flash(esp, args.block_format)
    remove(tmpfiles())
