import time
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import traceback

# Import your backend simulation class
from simBackend import Sim

# Initialize the Sim instance
sim_instance = Sim()



def start_simulation():
    try:
        num_flips = int(num_flips_entry.get())
        num_sims = int(num_sims_entry.get())
        wagers = list(map(int, wagers_entry.get().split(',')))

        threading.Thread(
            target=run_simulation_task,
            args=(num_sims, num_flips, wagers),
            daemon=True
        ).start()
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers.")
    except Exception as e:
        messagebox.showerror("Simulation Error", str(e))

def run_simulation_task(num_sims, num_flips, wagers):
    # This function should call the backend's simulation method and update the GUI accordingly
    # Including updating the progress bar, stats, and handling the violin plot data
    sim_instance.run_simulation_task(num_sims, num_flips, wagers, progress=update_progress)
    update_progress(0)
    update_wagers(wager_combobox, sim_instance.stats)
    # Automatically load the most recent statistics
    wagers1 = list(sim_instance.stats.keys())
    if sim_instance.stats:
        most_recent_wager = list(sim_instance.stats.keys())[-1]  # Assuming the last wager is the most recent
        update_stats_text(most_recent_wager, sim_instance.stats)

    window.after(0, lambda: update_wagers(wager_combobox, sim_instance.stats))
    if wagers:
        most_recent_wager = wagers1[-1]
        window.after(0, lambda: wager_combobox.set(most_recent_wager))

    # Display the violin plot for all wagers
    display_violin_plot_for_all_wagers(wagers1)

def update_progress(progress):
    def progress_update():
        progress_var.set(progress)
        progress_label.config(text=f"{progress:.2f}% Complete")

    # Schedule the update to be run on the main thread
    window.after(0, progress_update)

def update_stats_text(wager, stats):
    # # Clear the existing text
    stats_text.delete('1.0', tk.END)
    # Insert the stats for the selected wager, excluding the 'data' key
    if wager in stats:
        stats_text.insert(tk.END, f"Wager: {wager}\n")
        for key, value in stats[wager].items():
            if key != 'Data':
                stats_text.insert(tk.END, f"{key}: {value}\n")
    else:
        stats_text.insert(tk.END, "No statistics available for this wager.")

def update_wagers(wager_combobox, stats):
    # Clear the existing options
    wager_combobox['values'] = []
    # Populate the combobox with new wagers
    wager_combobox['values'] = list(stats.keys())


def on_wager_selection(event):
    # Get the selected wager size
    selected_wager = wager_combobox.get()
    # Update the statistics text area and violin plot
    update_stats_text(selected_wager, sim_instance.stats)
    display_violin_plot([selected_wager], canvas, figure)


def display_violin_plot(wagers, canvas, figure):
    stats = sim_instance.stats
    if len(wagers) == 1:
        data_for_plot = stats[wagers[0]]['Data']
    else:
        data_for_plot = [stats[wager]['Data'] for wager in wagers if wager in stats and len(stats[wager]['Data']) > 0]

    figure.clf()
    ax = figure.add_subplot(111)
 # Check if there is data to plot
    ax.violinplot(data_for_plot)

    if len(wagers) == 1:
        ax.set_xticks([1])
        ax.set_xticklabels([str(wagers[0])])

    else:
        ax.set_xticks(np.arange(1, len(data_for_plot) + 1))
        ax.set_xticklabels([str(wager) for wager in wagers if wager in stats and len(stats[wager]['Data']) > 0])
    ax.set_title('Violin plot of Simulation Results')
    canvas.draw()

def display_violin_plot_for_all_wagers(wagers):
    display_violin_plot(wagers, canvas, figure)

def calculate_drawdown_odds():
    try:

        drawdown_value = float(drawdown_entry.get())
        wager = wager_combobox.get()
        percentile = sim_instance.calculate_drawdown_percentile(wager, drawdown_value)
        percentile_result_label.config(
            text=f"Percentile: {percentile:.2f}% for drawdown {drawdown_value} in wager {wager}")
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number for drawdown value.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def calculate_backstop():
    try:
        percentile = float(percentile_entry.get())
        wager = wager_combobox.get()
        backstop = sim_instance.calculate_backstop(wager, percentile)
        percentile_result_label.config(
            text=f"Backstop for {percentile:.2f}% for wager {wager}: {backstop:.2f}")
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number for drawdown value.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def reset_simulation():
    sim_instance.stop_java_process()
    sim_instance.stop_threads.set()
    time.sleep(0.1)
    sim_instance.stop_threads.clear()

def on_app_exit():
    # Handle clean-up tasks, such as stopping any running simulation threads
    window.destroy()


window = tk.Tk()
window.title("Coin Flip Simulation")
# Create and place input fields and labels
tk.Label(window, text="Number of flips:").pack()
num_flips_entry = tk.Entry(window)
num_flips_entry.pack()

tk.Label(window, text="Number of simulations:").pack()
num_sims_entry = tk.Entry(window)
num_sims_entry.pack()

tk.Label(window, text="Wagers (comma separated):").pack()
wagers_entry = tk.Entry(window)
wagers_entry.pack()

# Button to run the simulation
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(window, length=200, variable=progress_var, maximum=100)
progress_bar.pack()

# Label to display the progress text
progress_label = tk.Label(window, text="0 / 0 flips (0%)")
progress_label.pack()

# Create the start button and assign the start_simulation function to the command
start_button = tk.Button(window, text="Start Simulation", command=start_simulation)
start_button.pack()

reset_button = tk.Button(window, text="Reset Simulation", command=reset_simulation)
reset_button.pack()

figure = plt.Figure(figsize=(6, 4), dpi=100)
canvas = FigureCanvasTkAgg(figure, master=window)  # A tk.DrawingArea.
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

from tkinter import font
# Progress bar setup
wager_label = tk.Label(window, text="Stats and 95% Confidence Interval for wager:")
wager_label.pack()
wager_combobox = ttk.Combobox(window, values=[])
wager_combobox.pack()
wager_combobox.bind("<<ComboboxSelected>>", on_wager_selection)
bold_font = font.Font(family="Helvetica", size=10, weight="bold")
percentile_result_label = tk.Label(window, text="", font=bold_font)
percentile_result_label.pack()
tk.Label(window, text="Enter Drawdown for Percentile Calculation:").pack()
drawdown_entry = tk.Entry(window)
drawdown_entry.pack()
# Button to trigger drawdown odds calculation
drawdown_odds_button = tk.Button(window, text="Calculate Drawdown Odds", command=calculate_drawdown_odds)
drawdown_odds_button.pack()
tk.Label(window, text="Enter Percentile for Backstop (Drawdown) Calculation:").pack()
percentile_entry = tk.Entry(window)
percentile_entry.pack()

backstop_button = tk.Button(window, text="Calculate Backstop for Percentile", command=calculate_backstop)
backstop_button.pack()

# Text widget for displaying statistics, as before
stats_text = tk.Text(window, height=10, width=50)
stats_text.pack()



window.protocol("WM_DELETE_WINDOW", on_app_exit)


# Main loop for the GUI
window.mainloop()