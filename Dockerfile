FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

# Install the 64-bit toolchain for a 64-bit kernel
RUN apt-get update && apt-get install -y \
    git \
    bc \
    bison \
    flex \
    libssl-dev \
    make \
    libc6-dev \
    libncurses5-dev \
    crossbuild-essential-arm64 \
    sed \
    g++ \
    device-tree-compiler \
    wget

# Get the source code from yocto branch and balena commit & 64-bit build with configs for CM4
RUN wget -O linux-raspberrypi_5.4.bb http://git.yoctoproject.org/cgit/cgit.cgi/meta-raspberrypi/tree/recipes-kernel/linux/linux-raspberrypi_5.4.bb?h=dunfell && \
    wget -O linux-raspberrypi_5.4.bbappend https://github.com/balena-os/balena-raspberrypi/blob/master/layers/meta-balena-raspberrypi/recipes-kernel/linux/linux-raspberrypi_5.4.bbappend && \
    BRANCH=$(sed '/BRANCH ?= "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' linux-raspberrypi_5.4.bb) && \
    HASH_COMMIT=$(sed '/SRCREV_machine = &quot;/!d;s//&\n/;s/.*\n//;:a;/&/bb;$!{n;ba};:b;s//\n&/;P;D' linux-raspberrypi_5.4.bbappend) && \
    git clone --branch $BRANCH https://github.com/raspberrypi/linux.git && \
    git checkout $HASH_COMMIT && \
    git reset --hard && \
    cd linux && \
    KERNEL=kernel8 && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
    make -j 6 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs

# Change the default shell from /bin/sh to /bin/bash
SHELL ["/bin/bash", "-c"]

# Get AutoBSP and generate dtbo
CMD  cp ../data/dts/upverter-overlay.dts linux/arch/arm/boot/dts/overlays/ && \
     cd /linux/arch/arm/boot/dts/overlays && \
     cpp -nostdinc -I include -I arch -undef -x assembler-with-cpp upverter-overlay.dts upverter.dts.preprocessed && \
     dtc -I dts -O dtb -o upverter.dtbo upverter.dts.preprocessed && \
     sed '/\wm8960-soundcard.dtbo/a dtbo-y += upverter.dtbo'  /linux/arch/arm/boot/dts/overlays/Makefile && \
     cd /linux  && \
     KERNEL=kernel8  && \
     make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
     make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs && \
     mkdir -p /data/dtbo && \
     cp /linux/arch/arm/boot/dts/overlays/upverter.dtbo ../data/dtbo/upverter.dtbo
