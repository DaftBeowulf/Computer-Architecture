"""CPU functionality."""

import sys
import time


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256
        self.reg = [0] * 7 + [len(self.ram)-12]
        # final register reserved for SP -- grows downward, and final 11 blocks are reserved for other uses
        self.pc = 0
        self.time = time.time()
        # will be bit-& operated on with  the last the bits denoting LT, E, GT
        self.fl = 0b00000000
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
            0b00010011: self.i_ret,
            0b01010100: self.jmp,
            0b01001000: self.pra,
            0b10100111: self.cmp
        }

    def ram_read(self, address):
        """
        Reads a stored value at the given address in memory.
        """
        return self.ram[address]

    def ram_write(self, address, val):
        """
        Stores a value into a block of memory at the given address.
        """
        self.ram[address] = val

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
        val_a = self.reg[reg_a]
        val_b = self.reg[reg_b]
        if op == "ADD":
            self.reg[reg_a] += val_b
        elif op == "MUL":
            self.reg[reg_a] *= val_b
        elif op == "CMP":
            if val_a < val_b:
                self.fl = self.fl | 0b00000100
            elif val_a == val_b:
                self.fl = self.fl | 0b00000010
            elif val_a > val_b:
                self.fl = self.fl | 0b00000001

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
        """
        Run the CPU.
        Checks each second for an interrupt flag.
        """
        IS = 6
        while True:
            # fetch corresponding command from an instruction list instead of using large if/else block
            new_time = time.time()
            if new_time - self.time >= 1:
                # at least one second has passed since self.time was last set
                # trigger timer by setting the Interrupt Status from 0 to 1
                self.reg[IS] = 1

                # set new time for next 1-sec increment
                self.time = new_time

            if self.reg[IS] >= 1:  # key interrupts enabled
                self._interrupts_enabled()

            ir = self.ram[self.pc]
            if ir in self.instructions and self.instructions[ir] == "HLT":
                break
            elif ir in self.instructions:
                self.instructions[ir]()
            else:
                print(f"Unknown command at pc index {self.pc}")
                self.trace()
                sys.exit(1)

    def _interrupts_enabled(self):
        """
        Uses masking and bitshifting to find out which interrupt was triggered. Pushes all
        relevant CPU state onto the stack until interrupt loop is complete.
        """
        # Storing Interrupt Mask and Interrupt Status register indexes
        IM = 5
        IS = 6

        # Mask out all interrupts we aren't interested in
        masked_interrupts = self.reg[IM] & self.reg[IS]
        for i in range(8):
            # each bit checked to see if one of the 8 interrupts happend
            interrupt_happened = ((masked_interrupts >> i) & 1) == 1
            if interrupt_happened:
                # clear bit in IS
                self.reg[IS] = 0

                # PC register pushed on the stack
                self.push(self.pc)

                # FL register pushed on the stack
                # TODO: Flags not currently used -- no CMP instructions handled yet

                # The address of the appropriate handler looked up from interrupt table
                # Should be for 0 (Timer interrupt)
                # i will be zero when IS set to 000000001, other values would be different bits => different interrupt vector
                handler_address = self.ram_read(0xF8 + i)

                # Registers R0-R6 pushed on the stack in that order
                for j in range(0, 7):
                    self.push(self.reg[j])

                # Set the PC to the handler address
                self.pc = handler_address

                # Disable further interrupt checks until Interrupt Return has occurred
                break

    def i_ret(self):
        """
        Returns from interrupt loop, retrieves all CPU state from before interrupt began.
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

    def ldi(self):
        """
        Loads a value into a specific address in registry.
        """
        reg_address = self.ram_read(self.pc + 1)
        reg_value = self.ram_read(self.pc + 2)

        self.reg[reg_address] = reg_value
        self.pc += 3

    def prn(self):
        """
        Prints the value stored at the specific address in registry.
        """
        reg_address = self.ram_read(self.pc + 1)
        print(f"{self.reg[reg_address]}")
        self.pc += 2

    def mul(self):
        """
        ALU is passed the next two inputs (register addresses)
        and multiplies the values stored there.
        Stores the result in the first register address.
        """
        reg_a = self.ram_read(self.pc + 1)
        reg_b = self.ram_read(self.pc + 2)
        self.alu('MUL', reg_a, reg_b)
        self.pc += 3

    def add(self):
        """
        ALU is passed two register addresses and stores 
        their sum at the first address.
        """
        reg_a = self.ram_read(self.pc + 1)
        reg_b = self.ram_read(self.pc + 2)
        self.alu('ADD', reg_a, reg_b)
        self.pc += 3

    def push(self, val=None):
        """
        Pushes a value onto the allocated portion of memory for the stack.
        Grows downward from the top of memory as values are added.
        If passed a value as a parameter, pushes that onto the stack instead 
        of reading from the next line of instruction.
        """
        sp = self.reg[7]  # Stack Pointer is held in reserved R07
        if val is not None:  # check if push is being used internally for other functions
            self.ram_write(sp-1, val)

        else:
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
        """
        If a return value is requested (internal use in other functions),
        removes latest item from the stack in memory and returns it.
        Otherwise, pops item from stack and sets to registry address
        from next line of instruction.
        """
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
        """
        Stores return address in stack and sets PC to address specified in instruction.
        """
        # push return address to the stack
        return_address = self.pc + 2
        self.push(return_address)

        #  Set the PC to the value in the register
        reg_val = self.ram_read(self.pc + 1)
        sub_address = self.reg[reg_val]
        self.pc = sub_address

    def ret(self):
        """
        Pops return address added in call() from the stack and sets the PC back to it.
        """
        # pop the return address off the stack
        return_address = self.pop(return_val=True)

        # store in the pc so the CPU knows which instruction to pick up at
        self.pc = return_address

    def store(self):
        """
        Using two register addresses from instruction, stores a value
        at a specific memory address.
        """
        reg_a = self.ram_read(self.pc + 1)
        reg_b = self.ram_read(self.pc + 2)

        target_address = self.reg[reg_a]
        target_val = self.reg[reg_b]

        self.ram_write(target_address, target_val)
        self.pc += 3

    def pra(self):
        """
        Prints the alphanumeric character of an ASCII number at the given registry address.
        """
        reg_address = self.ram_read(self.pc + 1)
        ascii_num = self.reg[reg_address]
        print(chr(ascii_num))
        self.pc += 2

    def jmp(self):
        """
        Sets the PC to the given jump address.
        """
        jump_address = self.ram_read(self.pc + 1)
        self.pc = self.reg[jump_address]

    def cmp(self):
        """
        ALU is passed two register address and stores whether registerA
        is less than, equal to, or greater than register B in the FL flag.
        """
        reg_a = self.ram_read(self.pc + 1)
        reg_b = self.ram_read(self.pc + 2)
        self.alu('CMP', reg_a, reg_b)
        self.pc += 3
