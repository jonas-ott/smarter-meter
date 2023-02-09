#!/usr/bin/env python3

from datetime import datetime
from datetime import timedelta
from datetime import time
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import matplotlib.dates as mdates
import requests

# Eine Umdrehung = 1/75 kWH
TURN_INC = 1 / 75

# Kosten für Zweitarif-Vertrag, bei nur einem Tarif beide Werte gleich setzen
START_LOW = time(hour=21, minute=55)
STOP_LOW = time(hour=5, minute=55)
COST_HIGH = 0.3
COST_LOW = 0.2

DAY_SECONDS = 24 * 60 * 60


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

    energy_daily = []
    cost_daily = []
    days = []
    prev = times[0]
    counter_energy = TURN_INC
    counter_cost = TURN_INC * COST_HIGH
    for x in times:
        if x.day != prev.day:
            energy_daily.append(counter_energy)
            cost_daily.append(counter_cost)
            days.append(prev.date())
            counter_energy = 0
            counter_cost = 0

        if x.time() > START_LOW or x.time() < STOP_LOW:
            counter_cost += TURN_INC * COST_LOW
        else:
            counter_cost += TURN_INC * COST_HIGH

        counter_energy += TURN_INC
        prev = x
    days.append(times[-1].date())
    energy_daily.append(counter_energy)
    cost_daily.append(counter_cost)

    return times, power, energy, days, energy_daily, cost_daily


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
            .format(ax_coord[1], y, datetime.utcfromtimestamp(x * DAY_SECONDS).strftime('%H:%M:%S'))

    return format_coord


def plot():
    plt.rcParams.update({'font.size': 12})
    px = 1 / plt.rcParams['figure.dpi']
    small_text = 13
    big_text = 16

    times, power, energy, days, energy_daily, cost_daily = parse()

    # Kosten Übersicht
    fig_cost, ax_c = plt.subplots(figsize=(1920 * px, 1080 * px))
    plt.subplots_adjust(bottom=0.06, top=0.96, left=0.06, right=0.94)
    plt.title("Kosten Übersicht", fontsize=big_text)

    ax_c.bar(days, cost_daily, color="red")
    ax_c.set_xlabel("Zeit", fontsize=small_text)
    ax_c.set_ylabel("Kosten [€]", color="red", fontsize=small_text)
    ax_c.grid(True)

    # Stromverbrauch Übersicht
    fig_energy, ax_e = plt.subplots(figsize=(1920 * px, 1080 * px))
    plt.subplots_adjust(bottom=0.06, top=0.96, left=0.06, right=0.94)
    plt.title("Stromverbrauch Übersicht", fontsize=big_text)

    ax_e.bar(days, energy_daily, color="blue")
    ax_e.set_xlabel("Zeit", fontsize=small_text)
    ax_e.set_ylabel("Energie [kWh]", color="blue", fontsize=small_text)
    ax_e.grid(True)

    # Stromverbrauch Detail
    fig_detail, ax1 = plt.subplots(figsize=(1920 * px, 1080 * px))
    plt.subplots_adjust(bottom=0.1, top=0.96, left=0.06, right=0.94)
    ax2 = ax1.twinx()
    ax2.format_coord = make_format(ax2, ax1)
    plt.title("Stromverbrauch Detail", fontsize=big_text)

    ax1.plot(times, power, drawstyle='steps', color="red")
    ax1.set_xlabel("Zeit", fontsize=small_text)
    ax1.set_ylabel("Leistung [W]", color="red", fontsize=small_text)
    ax1.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(ax1.xaxis.get_major_locator(), show_offset=False))
    ax1.grid(True)

    ax2.plot(times, energy, color="blue")
    ax2.set_ylabel("Energie [kWh]", color="blue", fontsize=small_text)

    t_begin = datetime.utcfromtimestamp(0)
    t_slider = Slider(plt.axes([0.06, 0.02, 0.78, 0.03]), '', (times[0] - t_begin).days, (times[-1] - t_begin).days,
                      valinit=(times[-1] - t_begin).days,
                      valstep=1 / 24)

    text_box = ax1.text(0.04, 0.96, '', transform=ax1.transAxes, fontsize=small_text, verticalalignment='top',
                        bbox=dict(boxstyle='square', facecolor='white', alpha=0.5))

    # update slider, set axis limits
    def update(val):
        pos = t_slider.val
        first = -1
        last = -1
        for x in range(0, len(times)):
            if first == -1 and times[x] > datetime.utcfromtimestamp(pos * DAY_SECONDS):
                first = x

            if times[x] > datetime.utcfromtimestamp((pos + 1) * DAY_SECONDS):
                last = x
                break

        if last == -1:
            last = len(times) - 1

        text_box.set_text("{:.2f}kWh".format(energy[last] - energy[first]))
        t_slider.valtext.set_text(datetime.utcfromtimestamp(round(pos * DAY_SECONDS)).strftime("%Y-%m-%d %H:%M"))
        ax1.axis([pos, pos + 1, 0, max(power[first: last]) * 1.05])
        ax2.set_ylim(energy[first], energy[last] * 1.05 - energy[first] * 0.05)
        fig_detail.canvas.draw_idle()

    # set day with keys
    def on_key(event):
        if event.key == 'left':
            t_slider.set_val(max(t_slider.val - 1, t_slider.valmin))
        if event.key == 'right':
            t_slider.set_val(min(t_slider.val + 1, t_slider.valmax))
        if event.key == "f5":
            plot()
            plt.close(fig_cost)
            plt.close(fig_detail)
            plt.close(fig_energy)

    # set day with scroll-wheel
    def on_scroll(event):
        if event.button == 'up':
            t_slider.set_val(max(t_slider.val - 1 / 24, t_slider.valmin))
        if event.button == 'down':
            t_slider.set_val(min(t_slider.val + 1 / 24, t_slider.valmax))

    t_slider.on_changed(update)
    fig_detail.canvas.mpl_connect('key_press_event', on_key)
    fig_detail.canvas.mpl_connect('scroll_event', on_scroll)

    update(0)
    plt.show()


if __name__ == "__main__":
    plot()
