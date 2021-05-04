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

# Download the kernel and DT repos from NVIDIA (tag for meta-tegra L4T_VERSION)
# Get kernel source from OE4T/linux-meta-tegra using source revision info from Balena
RUN wget -O tegra-class https://raw.githubusercontent.com/OE4T/meta-tegra/master/classes/l4t_bsp.bbclass && \
    wget -O source-revision https://raw.githubusercontent.com/balena-os/balena-jetson/master/layers/meta-balena-jetson/recipes-kernel/linux/linux-tegra_%25.bbappend && \
    TAG_BRANCH=$(sed '/L4T_VERSION ?= "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' tegra-class) && \
    HASH_COMMIT=$(sed '/SRCREV = "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' source-revision) && \
    wget https://developer.nvidia.com/embedded/l4t/r32_release_v5.1/r32_release_v5.1/t210/jetson-210_linux_r32.5.1_aarch64.tbz2 && \
    tar xjf jetson-210_linux_r32.5.1_aarch64.tbz2 && \
    cd Linux_for_Tegra && \
    ./source_sync.sh -k tegra-l4t-r${TAG_BRANCH} && \
    cd sources/kernel 
#    git clone -b oe4t-patches-l4t-r${TAG_BRANCH:0:4} https://github.com/OE4T/linux-tegra-4.9.git && \
#    cd linux-tegra-4.9 && \
#    git checkout ${HASH_COMMIT} && \
#    git reset --hard
#    TEGRA_KERNEL_OUT=kernel-compiled && \
#    export CROSS_COMPILE=aarch64-linux-gnu- && \
#    export LOCALVERSION=-tegra && \
#    mkdir -p $TEGRA_KERNEL_OUT && \
#    make ARCH=arm64 O=$TEGRA_KERNEL_OUT tegra_defconfig && \
#    make ARCH=arm64 O=$TEGRA_KERNEL_OUT -j8

# Change the default shell from /bin/sh to /bin/bash
# SHELL ["/bin/bash", "-c"]

#CMD  cp data/dts/devicetree-jetson_nano.dts linux-tegra-4.9/arch/arm/boot/dts/overlays/ && \
#     DTB=$(    devicetree-jetson_nano.dtb \) && \
#     sed '/\dtbo-$(CONFIG_ARCH_BCM2835) += /a ${DTB}'  linux-tegra-4.9/arch/arm/boot/dts/overlays/Makefile && \
#     cd linux-tegra-4.9 && \
#     make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- tegra_defconfig && \
#     make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs && \
#     mkdir -p data/dtbo && \
#     cp linux/arch/arm/boot/dts/overlays/upverter.dtbo data/dtbo/upverter.dtbo
