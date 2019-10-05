#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    import bpy
except ModuleNotFoundError as e:
    print("Blender 'bpy' not available.", e)
    bpy = None


# based on
# https://www.geeksforgeeks.org/print-colors-python-terminal/
# Python program to print
# colored text and background
class colors:
    '''
        Colors class:
        reset all colors with colors.reset;
        two sub classes
            fg for foreground
            bg for background;
        use as colors.subclass.colorname.
        i.e. colors.fg.red or colors.bg.greenalso,
        the generic bold, disable, underline, reverse, strike through,
        and invisible work with the main class i.e. colors.bold
    '''

    reset = '\033[0m'
    bold = '\033[01m'
    disable = '\033[02m'
    underline = '\033[04m'
    reverse = '\033[07m'
    strikethrough = '\033[09m'
    invisible = '\033[08m'

    class fg:
        black = '\033[30m'
        red = '\033[31m'
        green = '\033[32m'
        orange = '\033[33m'
        blue = '\033[34m'
        purple = '\033[35m'
        cyan = '\033[36m'
        lightgrey = '\033[37m'
        darkgrey = '\033[90m'
        lightred = '\033[91m'
        lightgreen = '\033[92m'
        yellow = '\033[93m'
        lightblue = '\033[94m'
        pink = '\033[95m'
        lightcyan = '\033[96m'

    class bg:
        black = '\033[40m'
        red = '\033[41m'
        green = '\033[42m'
        orange = '\033[43m'
        blue = '\033[44m'
        purple = '\033[45m'
        cyan = '\033[46m'
        lightgrey = '\033[47m'


def print_colored(mode, data):
    printcolor = colors.reset
    if mode == {'INFO'}:
        printcolor = colors.fg.lightblue
    elif mode == {'WARNING'}:
        printcolor = colors.fg.orange
    elif mode == {'ERROR'}:
        printcolor = colors.fg.red
    print("{}{}{}".format(printcolor, data, colors.reset))


# https://blender.stackexchange.com/a/142317/16634
def print_blender_console(mode, data):
    message_type = mode.pop()
    if message_type is 'WARNING':
        message_type = 'ERROR'
    if bpy:
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'CONSOLE':
                    override = {'window': window, 'screen': screen, 'area': area}
                    bpy.ops.console.scrollback_append(
                        override, text=str(data), type=message_type)


def print_console(mode, data):
    print_colored(mode, data)
    print_blender_console(mode, data)


def print_multi(mode, data, report=None):
    print_colored(mode, data)
    if report:
        report(mode, data)
    else:
        print_blender_console(mode, data)


# def print_info(mode, data):
#     if bpy:
#         for window in bpy.context.window_manager.windows:
#             screen = window.screen
#             for area in screen.areas:
#                 if area.type == 'INFO':
#                     override = {'window': window, 'screen': screen, 'area': area}
#                     bpy.ops.console.scrollback_append(
#                         override, text=str(data), type="OUTPUT")
#     else:
#         print(mode, data)
