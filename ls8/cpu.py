"""CPU functionality."""

import sys


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256
        # hard-coded for now, will test programmatic after test
        self.reg = [0] * 7 + [len(self.ram)-12]
        # final register reserved for SP -- grows downward, and final 11 blocks are reserved for other uses
        self.pc = 0
        self.instructions = {
            0b00000001: "HLT",
            0b10000010: self.ldi,
            0b01000111: self.prn,
            0b10100010: self.mul,
            0b01000101: self.push,
            0b01000110: self.pop
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

    def push(self):
        sp = self.reg[7]  # Stack Pointer is held in reserved R07

        # Originally checked for S/O prior to core function, but Beej
        # pointed out that the computer is interested in being as fast as possible
        # which means you don't want to do this check every time when it is almost
        # never in danger of occuring
        #
        # # if danger of stack overflow, print warning and exit
        # if sp-1 == self.pc:
        #     print("Stack overflow!")
        #     self.trace()
        #     return

        # grab next instruction for register address containing value
        reg_address = self.ram_read(self.pc + 1)
        reg_val = self.reg[reg_address]

        # store value in the next available slot in RAM apportioned to the stack (lower in memory)
        self.ram_write(sp-1, reg_val)

        # increment PC and decrement SP accordingly
        self.pc += 2
        self.reg[7] = sp - 1

    def pop(self):
        sp = self.reg[7]

        # see above with S/O
        # # if the stack is empty, do nothing and print an error
        # if sp == len(self.ram)-11:
        #     print("Error! Attempted to pop from stack while stack was empty")
        #     self.trace()
        #     return

        # grab next instruction for address that will contain the popped value
        reg_address = self.ram_read(self.pc + 1)

        # Grab the value at the current Stack Pointer address in memory
        popped_val = self.ram_read(sp)

        # Add popped_val to the specified register address
        self.reg[reg_address] = popped_val

        # Set current block in stack memory to zero and move lower in the stack (higher in memory)
        self.ram_write(sp, 0)
        self.reg[7] = sp + 1

        # Increment PC accordingly
        self.pc += 2
