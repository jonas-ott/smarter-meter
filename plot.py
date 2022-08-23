#!/usr/bin/env python3

from datetime import datetime
import math
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import requests

# Eine Umdrehung = 1/75 kWH
TURN_INC = 1 / 75


def parse():
    url = "http://192.168.178.28:8000/log.csv"
    lines = requests.get(url).text.split('\n')
    lines.pop()

    # file = open("log/log.csv", 'r')
    # lines = file.readlines()
    # im for loop muss in times.append... : "line" auf "line[:-1]" geändert werden

    times = []

    for line in lines:
        times.append(datetime.strptime(line, "%Y-%m-%d %H:%M:%S.%f"))

    delta_t = []
    for x in range(0, len(times) - 1):
        delta_t.append(times[x + 1] - times[x])

    power = [0]
    for delta in delta_t:
        # P = E/t
        # 1 Turn = 1000/75 Wh = 1000/75 * 60 * 60 Ws
        power.append(1000 * TURN_INC * 60 * 60 / (delta.total_seconds()))

    energy = []
    for x in range(0, len(power)):
        energy.append(x * TURN_INC)

    return times, power, energy


# https://stackoverflow.com/a/21585524
def make_format(current, other):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        # convert to display coords
        display_coord = current.transData.transform((x, y))
        inv = other.transData.inverted()
        # convert back to data coords with respect to ax
        ax_coord = inv.transform(display_coord)
        return 'Leistung: {:.0f}W   Verbrauch: {:.2f}kWh   Zeit: {}' \
            .format(ax_coord[1], y, datetime.utcfromtimestamp(x * 24 * 60 * 60).strftime('%H:%M:%S'))

    return format_coord


def plot():
    plt.rcParams.update({'font.size': 12})
    small_text = 13
    big_text = 16

    times, power, energy = parse()

    px = 1 / plt.rcParams['figure.dpi']
    fig, ax1 = plt.subplots(figsize=(1920 * px, 1080 * px))
    plt.subplots_adjust(bottom=0.1, top=0.96, left=0.06, right=0.94)
    ax2 = ax1.twinx()
    ax2.format_coord = make_format(ax2, ax1)
    plt.title("Stromverbrauch", fontsize=big_text)

    ax1.plot(times, power, drawstyle='steps', color="red")
    ax1.set_xlabel("Zeit", fontsize=small_text)
    ax1.set_ylabel("Leistung [W]", color="red", fontsize=small_text)
    ax1.grid(True)

    ax2.plot(times, energy, color="blue")
    ax2.set_ylabel("Energie [kWh]", color="blue", fontsize=small_text)

    t_begin = datetime.utcfromtimestamp(0)
    t_slider = Slider(plt.axes([0.06, 0.02, 0.78, 0.03]), '', (times[0] - t_begin).days, (times[-1] - t_begin).days,
                      valinit=(times[-1] - t_begin).days,
                      valstep=1 / 24)

    # update slider, set axis limits
    def update(val):
        pos = t_slider.val
        first = -1
        last = -1
        for x in range(0, len(times)):
            if first == -1 and (times[x] - t_begin).days == math.floor(pos):
                first = x

            if (times[x] - t_begin).days == math.ceil(pos + 1):
                last = x
                break

        if last == -1:
            last = len(times) - 1

        t_slider.valtext.set_text(datetime.utcfromtimestamp(round(pos * 24 * 60 * 60)).strftime("%Y-%m-%d %H:%M"))
        ax1.axis([pos, pos + 1, 0, max(power[first: last]) * 1.05])
        ax2.set_ylim(energy[first], energy[last] * 1.05 - energy[first] * 0.05)
        fig.canvas.draw_idle()

    # set day with keys
    def on_key(event):
        if event.key == 'left':
            t_slider.set_val(max(t_slider.val - 1, t_slider.valmin))
        if event.key == 'right':
            t_slider.set_val(min(t_slider.val + 1, t_slider.valmax))
        if event.key == "f5":
            plot()
            plt.close(fig)

    # set day with scroll-wheel
    def on_scroll(event):
        if event.button == 'up':
            t_slider.set_val(max(t_slider.val - 1 / 24, t_slider.valmin))
        if event.button == 'down':
            t_slider.set_val(min(t_slider.val + 1 / 24, t_slider.valmax))

    t_slider.on_changed(update)
    fig.canvas.mpl_connect('key_press_event', on_key)
    fig.canvas.mpl_connect('scroll_event', on_scroll)

    update(0)
    plt.show()


if __name__ == "__main__":
    plot()