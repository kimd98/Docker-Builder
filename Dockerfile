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
RUN wget -O kernel-source https://raw.githubusercontent.com/OE4T/meta-tegra/07f15cec44977dfba279062b36241e31b130ebfa/recipes-kernel/linux/linux-tegra_4.9.bb && \
    wget -O source-revision https://raw.githubusercontent.com/balena-os/balena-jetson/master/layers/meta-balena-jetson/recipes-kernel/linux/linux-tegra_%25.bbappend && \
    CLASS_TEGRA=$(sed '/inherit /!d;s//&\n/;s/.*\n//;:a;/require/bb;$!{n;ba};:b;s//\n&/;P;D' kernel-source) && \
    wget -O meta-tegra-class https://raw.githubusercontent.com/OE4T/meta-tegra/07f15cec44977dfba279062b36241e31b130ebfa/classes/${CLASS_T$
    SOURCE_CODE=$(sed '/SRC_REPO = "/!d;s//&\n/;s/.*\n//;:a;/;/bb;$!{n;ba};:b;s//\n&/;P;D' kernel-source) && \
    HASH_COMMIT=$(sed '/SRCREV = "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' source-revision) && \
    BRANCH=$(sed '/SRCBRANCH = "/!d;s//&\n/;s/.*\n//;:a;/$/bb;$!{n;ba};:b;s//\n&/;P;D' kernel-source) && \
    BRANCH_EXTENSION=$(sed '/VERSION ?= "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' meta-tegra-class) && \
    EXTENSION_1=$(sed 's/\..*/./' ${BRANCH_EXTENSION}) && \
    EXTENSION_2=$(sed '/${EXTENSION_1}/!d;s//&\n/;s/.*\n//;:a;/./bb;$!{n;ba};:b;s//\n&/;P;D' $BRANCH_EXTENSION) && \
    BRANCH_EXTENDED=$(${BRANCH}-l4t-r${EXTENSION_1}${EXTENSION_2}) && \
    git clone -b $BRANCH_EXTENDED https://${SOURCE_CODE}.git && \
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
     DTB=$(    upverter.dtbo \) && \
     sed '/\dtbo-$(CONFIG_ARCH_BCM2835) += /a ${DTB}'  linux/arch/arm/boot/dts/overlays/Makefile && \
     cd linux && \
     KERNEL=kernel8 && \
     make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
     make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs && \
     mkdir -p data/dtbo && \
     cp linux/arch/arm/boot/dts/overlays/upverter.dtbo data/dtbo/upverter.dtbo
