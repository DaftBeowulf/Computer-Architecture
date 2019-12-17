"""CPU functionality."""

import sys


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256
        self.reg = [0] * 8
        self.pc = 0
        self.instructions = {
            0b00000001: "HLT",
            0b10000010: self.ldi,
            0b01000111: self.prn,
            0b10100010: self.mul
        }

    def ram_read(self, mar):
        return self.ram[mar]

    def ram_write(self, mar, val):
        self.ram[mar] = val

    def load(self, filename):
        """Load a program into memory."""

        address = 0

        with open(filename) as f:
            for line in f:
                n = line.split('#')  # ignore everything to right of a comment
                n[0] = n[0].strip()  # remove all whitespace

                if n[0] == '':  # ignore blank or comment-only lines
                    continue
                # cast the binary command string to an integer
                val = int(n[0], 2)
                # store it at the current address in memory
                self.ram[address] = val
                address += 1

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        elif op == "MUL":
            self.reg[reg_a] = self.reg[reg_a] * self.reg[reg_b]
        else:
            raise Exception("Unsupported ALU operation")

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(f"TRACE: %02X | %02X %02X %02X |" % (
            self.pc,
            # self.fl,
            # self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')

        for i in range(8):
            print(" %02X" % self.reg[i], end='')

        print()

    def run(self):
        """Run the CPU."""
        while True:
            # fetch corresponding command from an instruction list instead of using large if/else block
            ir = self.ram[self.pc]

            if self.instructions[ir] == "HLT":
                break
            elif ir in self.instructions:
                self.instructions[ir]()
            else:
                print(f"Unknown command at pc index {self.pc}")
                self.trace()
                sys.exit(1)

    def ldi(self):
        reg_address = self.ram_read(self.pc + 1)
        reg_value = self.ram_read(self.pc + 2)

        self.reg[reg_address] = reg_value
        self.pc += 3

    def prn(self):
        print(f"{self.reg[self.ram[self.pc+1]]}")
        self.pc += 2

    def mul(self):
        """
        Passes the next two inputs (register addresses)
        and multiplies the values stored there.
        Stores the result in the first register address.

        Now has alu() run this since it's an ALU op
        """
        reg_a = self.ram_read(self.pc + 1)
        reg_b = self.ram_read(self.pc + 2)
        self.alu('MUL', reg_a, reg_b)
        self.pc += 3
