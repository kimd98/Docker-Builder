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
    wget

# Get the source code from yocto branch and balena commit & 64-bit build with configs for CM4
RUN wget -O kernel-source http://git.yoctoproject.org/cgit/cgit.cgi/meta-raspberrypi/tree/recipes-kernel/linux/linux-raspberrypi_5.4.bb?h=dunfell && \
    BRANCH=$(sed '/BRANCH ?= "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' kernel-source) && \
    HASH_COMMIT=$(sed '/SRCREV_machine = &quot;/!d;s//&\n/;s/.*\n//;:a;/&/bb;$!{n;ba};:b;s//\n&/;P;D' kernel-source) && \
    git clone --branch $BRANCH https://github.com/raspberrypi/linux.git && \
    cd linux && \
    git checkout $HASH_COMMIT && \
    git reset --hard && \
    KERNEL=kernel8 && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs

# Change the default shell from /bin/sh to /bin/bash
SHELL ["/bin/bash", "-c"]

# Get AutoBSP and generate dtbo
CMD  cp data/dts/upverter-overlay.dts linux/arch/arm/boot/dts/overlays/ && \
     sed '/\dtbo-$(CONFIG_ARCH_BCM2835) += /a upverter.dtbo'  linux/arch/arm/boot/dts/overlays/Makefile && \
     cd linux && \
     KERNEL=kernel8 && \
     make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
     make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs && \
     mkdir -p data/dtbo && \
     cp linux/arch/arm/boot/dts/overlays/upverter.dtbo data/dtbo/upverter.dtbo
