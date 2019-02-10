FROM balenalib/raspberrypi3-debian:stretch-run-20190127

ENV DEBIAN_FRONTEND=noninteractive

RUN install_packages python3 python3-pip python3-dbus python3-gi

COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

COPY . .

ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket
ENV UDEV=1

CMD ["bash", "scripts/start.sh"]