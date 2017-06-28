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

class cmsis_svd_sub_register():

    def __init__(self, register, args, register_value=None):
        self.register = register

        sub_regs = self.register.fields
        target_sub_register = args[0]

        self.sub_register = [s for s in sub_regs if s.name == target_sub_register][0]

        if (len(args) != 1):
            print "Fields do not take arguments"
            raise Exception("Fields do not take arguments")

    def print_register_field_info(self):
        f = self.sub_register
        gdb.write("\t ======= REGISTER FIELD  ====== \n")
        gdb.write("\t Name:                 {}\n".format(f.name))
        gdb.write("\t Description:          {}\n".format(f.description))
        gdb.write("\t Field Offset:         0x{:X}\n".format(f.bit_offset))
        gdb.write("\t Field Width:          {:X}\n".format(f.bit_width))
        gdb.write("\t Access:               {}\n".format(f.access))

    def print_info(self):
        self.print_register_field_info()

class cmsis_svd_registers():
    """
        Print information about the registers
    """

    #This function will check if args[0] exsists in the peripheral list
    def __init__(self, peripheral, args):
        self.peripheral = peripheral

        regs = self.peripheral.registers
        target_register = args[0]

        self.register = [r for r in regs if r.name == target_register][0]
        self.args = args[1:]

    def print_sub_registers(self):
        reg  = self.register
        sr = reg.fields

        s        =  max(sr, key=lambda(s): len(s.name))
        sr_width =  len(s.name) + 2

        sr_info = {}
        for s in sr:
            s_info = {}

            if(s.bit_width == 1):
                offset =  "[{}]".format(s.bit_offset)
            else:
                l = s.bit_offset + s.bit_width -1
                r = s.bit_offset
                offset = "[{}-{}]".format(l,r)

            reset_mask = ((1 << s.bit_width) - 1) << s.bit_offset
            reset_val = reg.reset_value & reset_mask

            s_info["offset"] = offset
            s_info["reset_val"] = reset_val
            sr_info[s.name] = s_info

        x = max(sr_info.keys(), key=lambda(k): len(sr_info[k]["offset"]))
        max_offset_width = len(sr_info[x]["offset"]) + 2

        #TODO: needs to be cleaned
        for s in sr[::-1]:
            offset = str(sr_info[s.name]["offset"])
            reset_val = str(sr_info[s.name]["reset_val"])

            row = "\t{}:{} {}{}{}{}{}\n".format(s.name,
                                      "".ljust(sr_width - len(s.name)),
                                      "*",
                                      "".ljust(4),
                                      offset,
                                      "".ljust(max_offset_width - len(offset)),
                                      reset_val)
            gdb.write(row)


    def print_register_info(self):
        r = self.register
        p = self.peripheral
        actual_addr_off = r.address_offset + p.base_address
        gdb.write("\t ======= REGISTER  ====== \n")
        gdb.write("\t Name:                 {}\n".format(r.name))
        gdb.write("\t Description:          {}\n".format(r.description))
        gdb.write("\t Base Address:         0x{:X}\n".format(actual_addr_off))
        gdb.write("\t Address Offset:       0x{:X}\n".format(r.address_offset))
        gdb.write("\t Address Size:         {}\n".format(r.size))
        gdb.write("\t Reset Value:          0x{:X}\n".format(r.reset_value))
        gdb.write("\t Reset Mask:           0x{:X}\n".format(r.reset_mask))
        gdb.write("\t Access:               {}\n".format(r.access))

    def print_info(self):
        if len(self.args) == 0:
            self.print_sub_registers()
        elif self.args[0].lower() == "info":
            self.print_register_info()
        else:
            try:
                field = cmsis_svd_sub_register(self.register, self.args)
                field.print_info()
            except:
                gdb.write("Invalid field register value\n")

class cmsis_svd_peripheral():
    """
    This class contains print, name desc, width etc sub registers
    """

    #This function will check if args[0] exsists in the peripheral list
    def __init__(self, parser, args):
        self.device = parser.get_device()

        ps = self.device.peripherals
        target_peripheral = args[0]

        self.peripheral = [p for p in ps if p.name == target_peripheral][0]
        self.args = args[1:]

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
            desc = r.description
            len_addr_offset = r.address_offset + p.base_address
            pad_baddr = "".ljust(base_addr_width - len(str(len_addr_offset)))
            pad_name  = "".ljust(name_width - len(r.name))
            row = "\t{}:{} 0x{:X} {} {}\n".format(r.name,
                                            pad_name,
                                            int(len_addr_offset),
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
        if len(self.args) == 0:
            self.print_registers()
        elif self.args[0].lower() == "info":
            self.print_peripheral_info()
        else:
            try:
                reg = cmsis_svd_registers(self.peripheral, self.args)
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

    def process_device(self, arg):
        if len(arg) == 0:
            gdb.write("Invalid arguments\n")

        #TODO: Need to create a table for these commands
        if arg[0].lower() == "info":
            self.print_device_info()
        elif arg[0].lower() == "cpu":
            self.print_cpu_info()
        elif arg[0].lower() == "all":
            self.print_device_info()
            self.print_cpu_info()
        else:
            try:
                p = cmsis_svd_peripheral(self.parser, arg)
            except:
                gdb.write("Invalid Entry\n")
            p.print_info()


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
        arg = gdb.string_to_argv(args)

        if len(arg) == 0:
            self.print_peripherals()
        else:
            self.process_device(arg)

if __name__ == "__main__":
   # testing function

    load_cmsis_svd()
