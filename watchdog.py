#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

apt install  libdbus-glib-1-dev libdbus-1-dev python3.7-dev
python3.7 -m pip install dbus-python

"""
import tailer
import re
import time
import datetime
import dbus


last_restart = None


def restart_unit(interface, unit_name='EthereumRun.service'):
    # Надо перезпускать не чаще 1 раза в час

    global last_restart
    print("GOTO RESTART!", datetime.datetime.now() , last_restart)
    if last_restart is None:
        last_restart = datetime.datetime.now()
    elif datetime.datetime.now() - last_restart <  datetime.timedelta(hours=1):
        return False
    last_restart = datetime.datetime.now()

    try:
       interface.RestartUnit(unit_name, 'fail')
       return True
    except dbus.exceptions.DBusException as error:
       print(error)
       return False

if __name__ == '__main__':
    sysbus = dbus.SystemBus()
    systemd1 = sysbus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
    # service = sysbus.get_object('org.freedesktop.systemd1', object_path=manager.GetUnit('EthereumRun.service'))
    logfile = None
    try:
        logfile = open('parity.log')
    except (FileNotFoundError, PermissionError) as err:
        exit("Error: Can't read logfile (%s)" % (err))
    #
    last_mesg_datetime = datetime.datetime.now()
    tail_fail = 0
    while True:
        last = None
        try:
            last = tailer.tail(logfile, 10)
        except Exception :
            tail_fail +=1
        else:
            tail_fail = 0

        if tail_fail == 30:
            print("DETECT tail_fail: ", datetime.datetime.now(), tail_fail)

            restart_unit(manager)

        if last:
            last_line = last[-1]
            if last_line == '':
                last_line = last[-2]
            splited_line = re.split(" ", last_line)
            print("splited_line", splited_line )
            date_time_str = " ".join(splited_line[0:2])
            try:
                date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
            except Exception as inst:
                continue
            delta = datetime.timedelta(minutes=5)
            if date_time_obj <= last_mesg_datetime:
                # чета долго оно пишет в файл
                if datetime.datetime.now() - date_time_obj > delta:
                    # больше 5 минут новых строк нет
                    print("DETECT: ", datetime.datetime.now(), date_time_obj)

                    restart_unit(manager)
            else:
                # чекаем что в отобранных строках есть строка Verifier
                data_last = "\n".join(last)
                # result = re.findall(r'^(\d+-\d+-\d+ \d+:\d+:\d+).+Verifier #\d+ INFO import  Imported #(\d+)', data_last, re.MULTILINE)
                result = re.findall(r'Verifier #\d+ INFO import  Imported #(\d+)', data_last, re.MULTILINE)
                if result:
                    last_val = None
                    restart_pr = 0
                    for val in result:
                        if last_val is None:
                            last_val = int(val)
                        else:
                            if last_val == int(val):
                                restart_pr += 1
                            elif last_val < int(val):
                                restart_pr = 0
                    if restart_pr > 0:
                        print("DETECT fail Verifier: ", result)
                        restart_unit(manager)
                else:
                    print("DETECT NO Verifier: ", last[-5:])
                    restart_unit(manager)

        time.sleep(31)
