import IEEE754

import FPMUL_InputMonitor
import FPMUL_OutputMonitor
import FPMUL_Scoreboard
import FPMUL_Generator

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.drivers import BitDriver
from cocotb.binary import BinaryValue


class FPMUL_TB:
    def __init__(self, dut):
        """
        
        """

        # Some internal state
        self.dut = dut
        self.stopped = False

        # Create input driver and output monitor
        self.input_driver = FPMUL_Driver()
        
        self.output_monitor = FPMUL_OutputMonitor(dut.Done, dut.Clk)
        
        # Create a scoreboard on the outputs
        self.expected_output = [ ]
        self.scoreboard = FPMUL_Scoreboard(dut) #create a floating point scoreboard? mostly just to check and log flags
        self.scoreboard.add_interface(self.output_monitor, self.expected_output)

        # Reconstruct the input transactions from the pins
        # and send them to our 'model'
        self.input_monitor = FPMUL_InputMonitor(dut.Start, dut.Clk, callback=self.model)

    def model(self, transaction):
        if not self.stopped:
            A, B = transaction
            product = A * B
            self.expected_output.append((A, B, product))

    def start(self):
        """Start generation of input data."""
        self.input_driver.start()

    def stop(self):
        """
        Stop generation of input data. 
        Also stop generation of expected output transactions.
        One more clock cycle must be executed afterwards, so that, output of
        """
        self.input_driver.stop()
        self.stopped = True

# ==============================================================================
@cocotb.coroutine
def clock_gen(signal):
    """Generate the clock signal."""
    while True:
        signal <= 0
        yield Timer(5000) # ps
        signal <= 1
        yield Timer(5000) # ps

# ==============================================================================
@cocotb.coroutine
def run_test(dut, A, B):
    """Setup testbench and run a test."""
    cocotb.fork(clock_gen(dut.Clk))
    tb = FPMUL_TB(dut)
    clk_edge = RisingEdge(dut.Clk)

    # Apply random input data by input_gen via Driver for 100 clock cycle.
    tb.start()
    dut.A = A.floatToBinary()
    dut.B = B.floatToBinary()
    dut.Start = 1
    yield clk_edge
    while not dut.Done:
        yield clk_edge

    # Stop generation of input data. One more clock cycle is needed to capture
    # the resulting output of the DUT.
    tb.stop()

    # Print result of scoreboard.
    raise tb.scoreboard.result

# ==============================================================================
# Register test.
factory = TestFactory(run_test)

factory.add_option("A", [
            FPMUL_Generator.randomFloat,
            FPMUL_Generator.randomNormalFloat,
            FPMUL_Generator.randomNanFloat,
            FPMUL_Generator.randomDenormalizedFloat,
            FPMUL_Generator.randomZeroFloat,
            FPMUL_Generator.randomInfinityFloat
        ]
    )

factory.add_option("B", [
            FPMUL_Generator.randomFloat,
            FPMUL_Generator.randomNormalFloat,
            FPMUL_Generator.randomNanFloat,
            FPMUL_Generator.randomDenormalizedFloat,
            FPMUL_Generator.randomZeroFloat,
            FPMUL_Generator.randomInfinityFloat
        ]
    )

factory.generate_tests()