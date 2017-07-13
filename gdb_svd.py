import os
import sys
import gdb
import re
import cmsis_svd
from cmsis_svd.parser import SVDParser

class load_cmsis_svd(gdb.Command):
    """ Load svd file from cmsis package.
        Give the name of the file and svd will automatically load it.
    """

    def __init__(self):
        gdb.Command.__init__(self, "load-cmsis-svd", gdb.COMMAND_DATA,
                             gdb.COMPLETE_FILENAME)

    def invoke(self, args, from_tty):
        print(args)
        try:
            c = str(args).split(" ")[0]
            gdb.write("Loading {}...\n".format(c))
        except:
            gdb.write("Please provide a chip name (load_cmsis_svd [chip name])\n")

        self.parser = SVDParser.for_packaged_svd("Freescale", c)
        self.device = self.parser.get_device()
        cmsis_svd(self.parser)
        gdb.write("Loaded file for device {} \n".format(self.device.name))

        gdb.write("Enable memory read\n")
        gdb.execute("set mem inaccessible-by-default off")

class cmsis_svd_register_field():

    def __init__(self, register, target_register_field, args = None, register_value=None):
        self.register = register

        fields = self.register.fields
        self.field = [f for f in fields if f.name == target_register_field][0]

        if register_value == None:
            self.register_value = 0
        else:
            self.register_value = register_value

        if args != None:
            print "Fields do not take arguments"
            raise Exception("Fields do not take arguments")

        self.__setup_field_values__()

    def __setup_field_values__(self):
        f = self.field
        if (f.bit_width == 1):
            self.offset =  "[{}]".format(f.bit_offset)
        else:
            l = f.bit_offset + f.bit_width -1
            r = f.bit_offset
            self.offset = "[{}-{}]".format(l,r)

        self.reset_mask = ((1 << f.bit_width) - 1) << f.bit_offset
        self.reset_val = self.register.reset_value & self.reset_mask
        self.field_value = (self.register_value & self.reset_mask) >> f.bit_offset

    def print_register_field_info(self):
        f = self.field
        gdb.write("\t ======= REGISTER FIELD  ====== \n")
        gdb.write("\t Name:                 {}\n".format(f.name))
        gdb.write("\t Description:          {}\n".format(f.description))
        gdb.write("\t Offset:               {}\n".format(self.offset))
        gdb.write("\t Field Width:          {:X}\n".format(f.bit_width))
        gdb.write("\t Field Offset:         0x{:X}\n".format(f.bit_offset))
        gdb.write("\t Reset Mask:           0x{:X}\n".format(self.reset_mask))
        gdb.write("\t Reset Value:          0x{:X}\n".format(self.reset_val))
        gdb.write("\t Access:               {}\n".format(f.access))

    def print_info(self):
        self.print_register_field_info()

class cmsis_svd_registers():
    """
        Print information about the registers
    """

    #This function will check if args[0] exsists in the peripheral list
    def __init__(self, peripheral, target_register, args = None):
        self.peripheral = peripheral

        regs = self.peripheral.registers
        self.register = [r for r in regs if r.name == target_register][0]

        self.args = args

        self.__setup_register_values__()

    def __setup_register_values__(self):
            self.address = self.peripheral.base_address + self.register.address_offset
            self.register_value = self.read()

    def read(self):
        r = self.register

        if 0 < r.size and r.size <= 8:
            bits = 8;
        elif 8 < r.size and r.size <= 16:
            bits = 16;
        else:
            bits = 32

        reg_read_command = "*(uint{}_t *)0x{:x}".format(bits,self.address)
        return int(gdb.parse_and_eval(reg_read_command))

    def print_register_fields(self):
        reg  = self.register
        fields = reg.fields

        f =  max(fields, key=lambda(f): len(f.name))
        field_name_width =  len(f.name) + 2

        row = "\t{}: 0x{:X}\n".format(reg.name, self.register_value)
        gdb.write(row)

        for f in fields[::-1]:
            f_obj = cmsis_svd_register_field(self.register, f.name,
                                        register_value = self.register_value)
            row = "\t{}:{} 0x{:X} {} {} {} {}\n".format(f.name,
                                      "".ljust(field_name_width - len(f.name)),
                                      f_obj.field_value,
                                      "".ljust(4),
                                      f_obj.offset,
                                      "".ljust(8 - len(f_obj.offset)),
                                      f_obj.reset_val)
            gdb.write(row)


    def print_register_info(self):
        r = self.register
        p = self.peripheral
        gdb.write("\t ======= REGISTER  ====== \n")
        gdb.write("\t Name:                 {}\n".format(r.name))
        gdb.write("\t Description:          {}\n".format(r.description))
        gdb.write("\t Base Address:         0x{:X}\n".format(self.address))
        gdb.write("\t Address Offset:       0x{:X}\n".format(r.address_offset))
        gdb.write("\t Address Size:         {}\n".format(r.size))
        gdb.write("\t Reset Value:          0x{:X}\n".format(r.reset_value))
        gdb.write("\t Reset Mask:           0x{:X}\n".format(r.reset_mask))
        gdb.write("\t Access:               {}\n".format(r.access))

    def print_info(self):
        if self.args == None:
            self.print_register_fields()
        elif self.args[0].lower() == "info":
            self.print_register_info()
        else:
            try:
                if len(self.args[1:]) == 0:
                    other_args = None
                else:
                    other_args = self.args[1:]

                field = cmsis_svd_register_field(self.register, self.args[0],
                                                 other_args,
                                                self.register_value)
                field.print_info()
            except:
                gdb.write("Invalid field register value\n")

class cmsis_svd_peripheral():
    """
    This class contains print, name desc, width etc sub registers
    """

    #This function will check if args[0] exsists in the peripheral list
    def __init__(self, parser, target_peripheral, args = None):
        self.device = parser.get_device()

        ps = self.device.peripherals
        self.peripheral = [p for p in ps if p.name == target_peripheral][0]

        self.args = args;

    def print_registers(self):
        rs = self.peripheral.registers
        p = self.peripheral

        name_width = 0
        base_addr_width = 0
        for r in rs:
            name_width = max(name_width, len(r.name))
            len_addr_offset = r.address_offset + p.base_address
            base_addr_width = max(base_addr_width, len(str(len_addr_offset)))

        name_width = name_width + 2
        base_addr_width = base_addr_width + 2

        for r in rs:
            r_obj = cmsis_svd_registers(self.peripheral, r.name)

            desc = r.description
            pad_baddr = "".ljust(base_addr_width - len(str(len_addr_offset)))
            pad_name  = "".ljust(name_width - len(r.name))
            row = "\t{}:{} 0x{:X}:0x{:02X} {} {}\n".format(r.name,
                                            pad_name,
                                            r_obj.address,
                                            r_obj.register_value,
                                            pad_baddr,
                                            desc)
            gdb.write(row)

    def print_peripheral_info(self):
        p = self.peripheral
        b = p.address_block
        gdb.write("\t ======= PERIPHERAL  ====== \n")
        gdb.write("\t Name:                 {}\n".format(p.name))
        gdb.write("\t Base Address:         0x{:X}\n".format(p.base_address))
        gdb.write("\t Prepend To Name:      {}\n".format(p.prepend_to_name))
        gdb.write("\t Group Name:           {}\n".format(p.group_name))
        gdb.write("\t Description:          {}\n".format(p.description))
        gdb.write("\t Address Usage:        {}\n".format(b.usage))
        gdb.write("\t Address Size:         0x{:X}\n".format(b.size))
        gdb.write("\t Address Offset:       0x{:X}\n".format(b.offset))

    def print_info(self):
        if self.args == None:
            self.print_registers()
        elif self.args[0].lower() == "info":
            self.print_peripheral_info()
        else:
            try:
                if (len(self.args) == 1):
                    other_args = None
                else:
                    other_args = self.args[1:]
                reg = cmsis_svd_registers(self.peripheral, self.args[0], other_args)
                reg.print_info()
            except:
                gdb.write("Invalid register value\n")

class cmsis_svd(gdb.Command):
    """ Run commands using cmsis svd to show information """

    def __init__(self, parser):
        gdb.Command.__init__(self, "info-svd", gdb.COMMAND_DATA)
        self.parser = parser
        self.device = self.parser.get_device()

    def print_peripherals(self):
        peripherals = self.device.peripherals

        name_width = 0
        base_addr_width = 0
        for p in peripherals:
            name_width = max(name_width, len(p.name))
            base_addr_width = max(base_addr_width, len(str(p.base_address)))

        name_width = name_width + 2
        base_addr_width = base_addr_width + 2

        for p in peripherals:
            desc = p._description
            pad_baddr = "".ljust(base_addr_width - len(str(p.base_address)))
            pad_name  = "".ljust(name_width - len(p.name))
            row = "\t{}:{} 0x{:X} {} {}\n".format(p.name,
                                            pad_name,
                                            int(p.base_address),
                                            pad_baddr,
                                            desc)
            gdb.write(row)

    def print_device_info(self):
        d = self.device
        gdb.write("\t ======= DEVICE ====== \n")
        gdb.write("\t Name:                 {}\n".format(d.name))
        gdb.write("\t Vendor:               {}\n".format(d.vendor))
        gdb.write("\t Vendor Id:            {}\n".format(d.vendor_id))
        gdb.write("\t Version:              {}\n".format(d.version))
        gdb.write("\t Address Unit Bits:    {}\n".format(d.address_unit_bits))
        gdb.write("\t Width:                {}\n".format(d.width))
        gdb.write("\t Size:                 {}\n".format(d.size))
        gdb.write("\t Description:          {}\n".format(d.description))

    def print_cpu_info(self):
        c = self.device.cpu
        gdb.write("\t ======= CPU ======= \n")
        gdb.write("\t Name:                 {}\n".format(c.name))
        gdb.write("\t Revision:             {}\n".format(c.revision))
        gdb.write("\t Endian:               {}\n".format(c.endian))
        gdb.write("\t Mpu Present:          {}\n".format(c.mpu_present))
        gdb.write("\t Fpu Present:          {}\n".format(c.fpu_present))
        gdb.write("\t Vtor Present:         {}\n".format(c.vtor_present))
        gdb.write("\t Nvic Prio Bits:       {}\n".format(c.nvic_prio_bits))
        gdb.write("\t Vendor Systick Config:{}\n".format(c.vendor_systick_config))

    def process_device(self):
        #TODO: Need to create a table for these commands
        #TODO: Handle argumetns to info, cpu etc
        if len(self.args) == 0:
            self.print_peripherals()
        elif self.args[0].lower() == "info":
            self.print_device_info()
        elif self.args[0].lower() == "cpu":
            self.print_cpu_info()
        elif self.args[0].lower() == "all":
            self.print_device_info()
            self.print_cpu_info()
        else:
            try:
                if (len(self.args) == 1):
                    other_args = None
                else:
                    other_args = self.args[1:]

                p = cmsis_svd_peripheral(self.parser, self.args[0], other_args)
                p.print_info()
            except:
                gdb.write("Invalid Entry\n")

    def invoke(self, args, from_tty):
        """
        info-svd - print all the PERIPHERALS
        info-svd all - print all information
        info-svd  - print all the peripherals
        info-svd UART0  - print all registers and values
        info-svd UART0 desc
        info-svd UART0 addr
        info-svd UART0 all
        info-svd UART0
        info-svd UART0 C1 - print all sub registers and values
        info-svd UART0 C1 desc
        info-svd UART0 C1 addr
        info-svd UART0 C1 all
        info-svd UART0 C1 TXEN - print value
        info-svd UART0 C1 TXEN desc - description
        info-svd UART0 C1 TXEN reset - value at reset
        info-svd UART0 C1 TXEN all - value
        """
        self.args = gdb.string_to_argv(args)
        self.process_device()

if __name__ == "__main__":
   # testing function

    load_cmsis_svd()
