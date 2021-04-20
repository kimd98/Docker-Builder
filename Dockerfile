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
    device-tree-compiler

# Get the source code & 64-bit build with configs for CM4
RUN git clone --depth=1 https://github.com/raspberrypi/linux && \
    cd linux && \
    KERNEL=kernel8 && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
    make -j 4 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs

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
