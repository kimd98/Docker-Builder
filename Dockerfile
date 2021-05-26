FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

# Install the 64-bit toolchain for a 64-bit kernel
RUN apt-get update && apt-get install -y \
    git \
    make \
    bc \
    crossbuild-essential-arm64 \
    sed \
    wget

# Change the default shell from /bin/sh to /bin/bash
SHELL ["/bin/bash", "-c"]

# Get kernel source from yocto OE4T/linux-meta-tegra using source revision info from Balena
RUN wget -O tegra-class https://raw.githubusercontent.com/OE4T/meta-tegra/master/classes/l4t_bsp.bbclass && \
    wget -O source-revision https://raw.githubusercontent.com/balena-os/balena-jetson/master/layers/meta-balena-jetson/recipes-kernel/linux/linux-tegra_%25.bbappend && \
    BRANCH=$(sed '/L4T_VERSION ?= "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' tegra-class) && \
    HASH_COMMIT=$(sed '/SRCREV = "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' source-revision) && \
    git clone -b oe4t-patches-l4t-r${BRANCH:0:4} https://github.com/OE4T/linux-tegra-4.9.git && \
    cd linux-tegra-4.9  && \
    git checkout $HASH_COMMIT && \
    git reset --hard && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- tegra_defconfig && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs

CMD cp /data/dts/devicetree-jetson_nano.dts /linux-tegra-4.9/nvidia/platform/t210/porg/kernel-dts/ && \
    sed -i '/makefile-path := /a dtb-y += devicetree-jetson_nano.dtb' /linux-tegra-4.9/nvidia/platform/t210/porg/kernel-dts/Makefile && \
    cd /linux-tegra-4.9 && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- tegra_defconfig && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs && \
    mkdir -p /data/dtb && \
    cp /linux-tegra-4.9/arch/arm64/boot/dts/_ddot_/_ddot_/_ddot_/_ddot_/nvidia/platform/t210/porg/kernel-dts/devicetree-jetson_nano.dtb /data/dtb/devicetree-jetson_nano.dtb
