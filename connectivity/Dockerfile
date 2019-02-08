FROM balenalib/raspberrypi3-debian

ENV DEBIAN_FRONTEND=noninteractive

RUN install_packages python3 python3-pip python3-dbus python3-gi

RUN pip3 install sanic python-networkmanager

COPY . .

ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket
ENV UDEV=1

CMD ["bash", "start.sh"]