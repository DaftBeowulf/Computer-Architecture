"""CPU functionality."""

import sys
import time


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256
        # hard-coded for now, will test programmatic after test
        self.reg = [0b00000000] * 7 + [len(self.ram)-12]
        # final register reserved for SP -- grows downward, and final 11 blocks are reserved for other uses
        self.pc = 0
        self.time = time.time()
        self.instructions = {
            0b00000001: "HLT",
            0b10000010: self.ldi,
            0b01000111: self.prn,
            0b10100010: self.mul,
            0b10100000: self.add,
            0b01000101: self.push,
            0b01000110: self.pop,
            0b01010000: self.call,
            0b00010001: self.ret,
            0b10000100: self.store,
            0b00010011: self.i_ret
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
            new_time = time.time()
            if new_time - self.time >= 1:
                # at least one second has passed since self.time was last set
                # trigger timer by setting the Interrupt Status from 0 to 1
                self.reg[IS] = 0b10000000

                # set new time for next 1-sec increment
                self.time = new_time

            if self.reg[6] == 1:  # interrupts enabled
                self._interrupts_enabled()

            if ir in self.instructions and self.instructions[ir] == "HLT":
                break
            elif ir in self.instructions:
                self.instructions[ir]()
            else:
                print(f"Unknown command at pc index {self.pc}")
                self.trace()
                sys.exit(1)

    def _interrupts_enabled(self):
        # Storing Interrupt Mask and Interrupt Status index for register to be more explicit
        IM = 5
        IS = 6

        # Mask out all interrupts we aren't interested in
        masked_interrupts = self.reg[IM] & self.reg[IS]
        for i in range(8):
            # each bit checked to see if one of the 8 interrupts happend
            interrupt_happened = ((masked_interrupts >> i) & 1) == 1
            if interrupt_happened:
                # clear bit in IS
                self.reg[IS] = 0b00000000

                # PC register pushed on the stack
                self.push(self.pc)

                # FL register pushed on the stack
                # TODO: Flags not currently used -- no CMP instructions handled yet

                # Registers R0-R6 pushed on the stack in that order
                for i in range(0, 7):
                    self.push(self.reg[i])

                # The address of the appropriate handler looked up from interrupt table
                # Should be for 0 (Timer interrupt)
                handler_address = self.ram_read(0xF8)

                # Set the PC to the handler address
                self.pc = handler_address

                # Disable further interrupt checks
                break

    def i_ret(self):
        """
        Returns from interrupt flow
        """
        # Registers R6-R0 popped from stack in that order
        for i in range(6, -1, -1):
            reg_val = self.pop(return_val=True)
            self.reg[i] = reg_val
        # FL register popped off the stack
        # TODO: FL not implemented yet

        # return address popped off the stack and stored in PC
        return_address = self.pop(return_val=True)
        self.pc = return_address
        # Interrupts re-enabled

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

    def add(self):
        reg_a = self.ram_read(self.pc + 1)
        reg_b = self.ram_read(self.pc + 2)
        self.alu('ADD', reg_a, reg_b)
        self.pc += 3

    def push(self, val=None):
        sp = self.reg[7]  # Stack Pointer is held in reserved R07
        if val is not None:  # check if push is being used internally for other functions
            self.ram_write(sp-1, val)

        else:  # another function not using it, this is from instruction
            # grab next instruction for register address containing value
            reg_address = self.ram_read(self.pc + 1)
            reg_val = self.reg[reg_address]

            # store value in the next available slot in RAM apportioned to the stack (lower in memory)
            self.ram_write(sp-1, reg_val)

            # increment PC and decrement SP accordingly
            self.pc += 2
        # either way sp gets decremented
        self.reg[7] = sp - 1

    def pop(self, return_val=False):
        sp = self.reg[7]

        if return_val is True:  # will have a value passed into pop() if ran from int_ret
            popped_val = self.ram_read(sp)
            self.reg[7] = sp + 1
            return popped_val

        else:
            # grab next instruction for address that will contain the popped value
            reg_address = self.ram_read(self.pc + 1)

            # Grab the value at the current Stack Pointer address in memory
            popped_val = self.ram_read(sp)

            # Add popped_val to the specified register address
            self.reg[reg_address] = popped_val

            # Move lower in the stack (higher in memory)
            self.reg[7] = sp + 1

            # Increment PC accordingly
            self.pc += 2

    def call(self):
        # push return address to the stack
        return_address = self.pc + 2
        self.reg[7] -= 1
        self.ram_write(self.reg[7], return_address)

        #  Set the PC to the value in the register
        reg_val = self.ram_read(self.pc + 1)
        sub_address = self.reg[reg_val]
        self.pc = sub_address

    def ret(self):
        # pop the return address off the stack
        return_address = self.ram_read(self.reg[7])
        self.reg[7] += 1

        # store in the pc so the CPU knows which instruction to pick up at
        self.pc = return_address

    def store(self):
        ram_address = self.ram_read(self.pc + 1)
        ram_value = self.ram_read(self.pc + 2)

        self.ram_write(ram_address, ram_value)
        self.pc += 3

    def pra(self):
        reg_address = self.ram_read(self.pc + 1)
        ascii_num = self.reg[reg_address]
        print(chr(ascii_num))
        self.pc += 2
