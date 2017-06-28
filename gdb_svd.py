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
            gdb.write("Invalid command\n")


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
