import os
import sys
import gdb
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




if __name__ == "__main__":
    # testing function

    load_cmsis_svd()
