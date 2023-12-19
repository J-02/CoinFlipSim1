import unittest
import subprocess
import time
import threading
import numpy as np

from simBackend import Sim
from unittest.mock import patch, MagicMock


class TestSim(unittest.TestCase):

    def setUp(self):
        # This method is called before each test
        # Create an instance of Sim class
        self.sim = Sim()

    def test_subprocess_return_code(self):
        # test that subprocess returns code
        self.sim.start_java_process()
        self.assertIsNone(self.sim.java_process.returncode, "Subprocess should be running")

    def test_subprocess_poll(self):
        # another run test
        self.sim.start_java_process()
        self.assertIsNone(self.sim.java_process.poll(), "Subprocess should be running")

    def test_subprocess_start_with_mock(self):
        # tests the process with mock
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()  # Mock the subprocess
            self.sim.start_java_process()
            mock_popen.assert_called_with(['java', '-jar', 'Flip.jar'],
                                          stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,  # Add this line
                                          text=True)

    def test_subprocess(self):
        # tests the subprocess returns the right data type and amount

        num_flips = 10  # Number of flips or simulations requested
        self.sim.start_java_process()
        # Assuming the subprocess is mocked and controlled
        # Use the actual method to get results from the subprocess
        simulation_output = self.sim.request_simulation_chunk(num_flips)

        # Verify the output is a string
        self.assertIsInstance(simulation_output, str, msg=f"{simulation_output} is not type string")

        # Convert the output to a list of outcomes
        outcomes = simulation_output.split(',')
        numsims = len(outcomes)
        # Check if the number of outcomes is as expected
        self.assertEqual(numsims, num_flips, msg=f"{outcomes} is not {num_flips} flips")
        self.sim.stop_java_process()

    def test_subprocess_failure_handling(self):
        # test incorrect input
        num_flips = 'asd'  # Number of flips or simulations requested
        self.sim.start_java_process()
        simulation_output = self.sim.request_simulation_chunk(num_flips)
        outcomes = simulation_output.split(',')
        self.assertEqual(outcomes[0], '', msg=f"{outcomes} is not {num_flips} flips")
        self.sim.stop_java_process()

    def test_process_sim_data(self):
        # tests that the sim_data is properly processed
        numflips = 100
        numSims = 200
        wagers = [1, 1, 2, 3, 4]
        self.sim.start_java_process()
        outcome = self.sim.process_sim_data(numSims, numflips, wagers, progress=None)
        outcomeShape = outcome.shape
        uniout = np.unique(outcome[:, :, 3])
        cumsum_per_sim = np.cumsum(outcome, axis=1)
        min_cumsum_per_sim = np.min(cumsum_per_sim, axis=1)
        stats = {i: self.sim.compute_statistics(min_cumsum_per_sim[idx]) for idx, i in enumerate(wagers)}
        single = self.sim.process_sim_data(numSims, numflips, [1], progress=None)
        singleshape = single.shape
        single_cumsum_per_sim = np.cumsum(single, axis=1)
        single_min_cumsum_per_sim = np.min(single, axis=1)

        # has assumed shape and multiplications done correctly
        self.assertEqual(outcomeShape, (numSims, numflips, len(wagers)), msg=f"{outcomeShape} is not (10, 100, 5)")
        self.assertTrue(set(uniout) == set([-3 + self.sim.fee * 3, 3 + self.sim.fee * 3]),
                        msg=f"only unique returns for wager 3 are {uniout} which is not {[-3 + self.sim.fee * 3, 3 + self.sim.fee * 3]}")

        # cum sum and min cum sum array shapes are correct
        self.assertEqual(cumsum_per_sim.shape,(numSims, numflips, len(wagers)))
        self.assertEqual(min_cumsum_per_sim.shape,(numSims, len(wagers)))

        # single wager
        self.assertEqual(singleshape, (numSims, numflips, 1))
        self.assertEqual(single_cumsum_per_sim.shape,(numSims, numflips, 1))
        self.assertEqual(single_min_cumsum_per_sim.shape,(numSims, 1))

        # proper data is returned
        stats = {i: self.sim.compute_statistics(min_cumsum_per_sim[:,idx]) for idx, i in enumerate(wagers)}
        data = stats[wagers[0]]["Data"]
        self.assertEquals(len(data), numSims)

    def test_data(self):
        # saves the data correctly

        numflips = 100
        numSims = 200
        wagers = [1, 1, 2, 3, 4]
        self.sim.run_simulation_task(numSims, numflips, wagers, progress=None)
        data = self.sim.stats['1 - 100 flips - 200 sims']['Data']
        print(data)
        self.assertEquals(len(data), numSims)


    def test_run_simulation_task(self):
        # sim task runs as expected and allows for duplicate sims
        numflips = 100
        numSims = 200
        wagers = [1, 1, 2, 3, 4]
        self.sim.run_simulation_task(numSims, numflips, wagers, progress=None)
        simcount = len(self.sim.stats.keys())
        self.assertTrue(simcount == 5, msg=f"Duplicate stats not working: {self.sim.stats.keys()}")
        self.assertTrue(self.sim.stats.get("1 - 10 flips - 100 sims v2"))
        self.sim.run_simulation_task(100, 10, [1], progress=None)

    def test_threading(self):
        # tests threading stop and start
        num_flips = 10000
        num_sims = 100000
        wagers = [1, 1, 2, 3, 4]
        sim_thread = threading.Thread(
            target=self.sim.run_simulation_task,
            args=(num_sims, num_flips, wagers),
            daemon=True
        )

        sim_thread.start()

        time.sleep(1)
        self.assertTrue(sim_thread.is_alive())
        self.sim.stop_threads.set()
        sim_thread.join(timeout=5)
        self.assertFalse(sim_thread.is_alive())



    def tearDown(self):
        # This method is called after each test
        # Clean up or release any resources allocated in setUp
        self.sim.reset()
        self.sim.stop_java_process()
        pass


if __name__ == '__main__':
    unittest.main()
