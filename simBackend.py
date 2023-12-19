import subprocess
import time
import numpy as np
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
np.set_printoptions(suppress=True)
current_stats = {}
sim_versions = {}

class Sim():

    def __init__(self, fee=0.0014):
        self.java_process = None
        self.stats = {}
        self.sim_versions = {}
        self.fee = fee
        self.stop_threads = threading.Event()

    def reset(self):
        self.stats = {}
        self.sim_versions = {}
        self.stop_threads.set()
        self.stop_java_process()
        time.sleep(1)
        self.stop_threads.clear()

    def start_java_process(self):
        # initializes the java process for the sim
        self.java_process = subprocess.Popen(['java', '-jar', 'Flip.jar'],
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)

    def stop_java_process(self):
        if self.java_process == None:
            return
        else:  # Only attempt to stop if the process has been started
            try:
                self.java_process.terminate()
                self.java_process.wait()
                self.java_process = None  # Reset the java_process to None
            except Exception as e:
                error_message = f"An error occurred in simulation: {e}\n"
                error_message += traceback.format_exc()  # This will give you the traceback of the exception
                print(error_message)
                print(f"Error stopping Java process: {e}")

    def run_simulation_task(self, num_sims, num_flips, wagers, progress = None):

        self.start_java_process()
        outcome = self.process_sim_data(num_sims, num_flips, wagers, progress)

        # Process the collected results
        cumsum_per_sim = np.cumsum(outcome, axis=1)
        min_cumsum_per_sim = np.min(cumsum_per_sim, axis=1)
        stats = {i: self.compute_statistics(min_cumsum_per_sim[:, idx]) for idx, i in enumerate(wagers)}

        # Versioning for duplicate simulations
        wager_items = []
        for i in wagers:
            sim_key = f"{num_flips}_{num_sims}_{i}"
            self.sim_versions[sim_key] = self.sim_versions.get(sim_key, 0) + 1
            version_suffix = f" v{self.sim_versions[sim_key]}" if self.sim_versions[sim_key] > 1 else ""
            wager_items.append(f"{i} - {num_flips} flips - {num_sims} sims{version_suffix}")

        # Update the instance's stats dictionary with the new stats
        for i, wager_item in enumerate(wager_items):
            self.stats[wager_item] = stats[wagers[i]]
        # Always stop the Java process whether there was an error or not
        self.stop_java_process()

    def process_sim_data(self, num_sims, num_flips, wagers, progress=None):
        total_count = num_flips * num_sims * len(wagers)
        processed_count = 0
        outcomes = []
        try:
            for _ in range(0, total_count, num_sims):
                outcomes_chunk = self.request_simulation_chunk(num_sims)
                if outcomes_chunk is None or self.stop_threads.isSet():
                    print("The Java process has terminated unexpectedly.")
                    break
                outcomes_array = np.fromstring(outcomes_chunk, dtype=int, sep=',')
                processed_count += len(outcomes_array)
                progressp = processed_count / total_count * 100
                if progress:
                    progress(progressp)
                outcomes.append(outcomes_array)

            all_outcomes = np.concatenate(outcomes, dtype=float)
            outcome3d = all_outcomes.reshape((num_sims, num_flips, len(wagers)))
            outcome3d += self.fee  # Adjustment as per original logic
            outcome = np.einsum("k,ijk->ijk", wagers, outcome3d)
            return outcome

        except Exception as e:
            error_message = f"An error occurred in simulation: {e}\n"
            error_message += traceback.format_exc()  # This will give you the traceback of the exception
            print(error_message)

    def request_simulation_chunk(self, num_flips):

        try:
            print(f"{num_flips}", file=self.java_process.stdin, flush=True)  # Send the number of flips to the Java process
            outcomes = []
            while True:
                line = self.java_process.stdout.readline()
                if line.strip() == '':  # Check for end of chunk indicator
                    break
                outcomes.append(line.strip())
            return ','.join(outcomes)
        except Exception as e:
            error_message = f"An error occurred in simulation: {e}\n"
            error_message += traceback.format_exc()  # This will give you the traceback of the exception
            print(error_message)
            pass

    def compute_statistics(self, data, num_bootstrap_samples=1000, confidence_level=0.95):
        # Calculate mean
        mean = np.mean(data)
        minimum = np.min(data)
        maximum = np.max(data)
        # Calculate quartiles
        fivepercent = np.percentile(data, 5)
        Q1 = np.percentile(data, 25)
        Q2 = np.median(data)  # Median is the 50th percentile
        Q3 = np.percentile(data, 75)

        def bootstrap_confidence_interval(data, num_bootstrap_samples, confidence_level, func):
            bootstrapstats = []
            for _ in range(num_bootstrap_samples):
                sample = np.random.choice(data, size=len(data), replace=True)
                bootstrapstats.append(func(sample))
            lower_bound = np.percentile(bootstrapstats, (1 - confidence_level) / 2 * 100)
            upper_bound = np.percentile(bootstrapstats, (1 + confidence_level) / 2 * 100)
            return lower_bound, upper_bound

        ci_mean = bootstrap_confidence_interval(data, num_bootstrap_samples, confidence_level, np.mean)
        ci_median = bootstrap_confidence_interval(data, num_bootstrap_samples, confidence_level, np.median)

        statistics = {
            "mean": round(mean, 2),
            "min": round(minimum, 2),
            "max": round(maximum, 2),
            "Lowest 5%": round(fivepercent,2),
            "Q1": round(Q1, 2),
            "Median": round(Q2, 2),
            "Q3": round(Q3, 2),
            "CI_lower_mean": round(ci_mean[0], 2),
            "CI_upper_mean": round(ci_mean[1], 2),
            "CI_lower_median": round(ci_median[0], 2),
            "CI_upper_median": round(ci_median[1], 2),
            "Data": data
        }
        return statistics



    def calculate_drawdown_percentile(self, wager, drawdown_value, num_bootstrap_samples=10000):
        """
        Calculate the percentile of a specific drawdown value for a given wager.

        :param wager: The selected wager.
        :param drawdown_value: The drawdown value to find the percentile for.
        :param num_bootstrap_samples: Number of bootstrap samples to use.
        :return: The percentile of the specified drawdown value.
        """
        drawdown_value  = 0 - drawdown_value if (drawdown_value > 0) else drawdown_value


        if wager not in self.stats:
            print("data for the selected wager is not available.")
            return None

        data = self.stats[wager]['Data']

        # Bootstrap sampling to generate drawdown statistics
        def single_bootstrap_sample(_):
            return np.random.choice(data, size=len(data), replace=True)

        with ThreadPoolExecutor() as executor:
            bootstrapstats = list(executor.map(single_bootstrap_sample, range(num_bootstrap_samples)))

        # Flatten the bootstrap statistics and calculate the percentile
        flattened_stats = np.concatenate(bootstrapstats)
        percentile = np.sum(drawdown_value > flattened_stats) / len(flattened_stats) * 100
        return percentile

    def calculate_backstop(self, wager, target_percentile, num_bootstrap_samples=10000):
        """
        Calculate the drawdown value at a given percentile for a specific wager.

        :param wager: The selected wager.
        :param target_percentile: The target percentile to find the drawdown value for.
        :param num_bootstrap_samples: Number of bootstrap samples to use.
        :return: The drawdown value at the specified percentile.
        """
        if wager not in self.stats:
            print("Data for the selected wager is not available.")
            return None

        data = self.stats[wager]['Data']

        # Bootstrap sampling to generate drawdown statistics
        def single_bootstrap_sample(_):
            return np.random.choice(data, size=len(data), replace=True)

        with ThreadPoolExecutor() as executor:
            bootstrapstats = list(executor.map(single_bootstrap_sample, range(num_bootstrap_samples)))

        # Flatten the bootstrap statistics
        flattened_stats = np.concatenate(bootstrapstats)

        # Calculate the drawdown value at the specified percentile
        drawdown_value_at_percentile = np.percentile(flattened_stats, target_percentile)
        return drawdown_value_at_percentile