FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    make \
    bc \
    crossbuild-essential-arm64 \
    sed \
    wget \
    python3

SHELL ["/bin/bash", "-c"]

# Get kernel source from yocto OE4T/linux-meta-tegra & NVIDIA L4T driver package using source revision info from Balena
RUN wget -O tegra-class https://raw.githubusercontent.com/OE4T/meta-tegra/master/classes/l4t_bsp.bbclass && \
    wget -O source-revision https://raw.githubusercontent.com/balena-os/balena-jetson/master/layers/meta-balena-jetson/recipes-kernel/linux/linux-tegra_%25.bbappend && \
    BRANCH=$(sed '/L4T_VERSION ?= "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' tegra-class) && \
    HASH_COMMIT=$(sed '/SRCREV = "/!d;s//&\n/;s/.*\n//;:a;/"/bb;$!{n;ba};:b;s//\n&/;P;D' source-revision) && \
    git clone -b oe4t-patches-l4t-r${BRANCH:0:4} https://github.com/OE4T/linux-tegra-4.9.git && \
    wget https://developer.nvidia.com/embedded/l4t/r32_release_v5.1/r32_release_v5.1/t210/jetson-210_linux_r32.5.1_aarch64.tbz2 && \
    tar -jxvf *.tbz2 && \
    wget -O Linux_for_Tegra/bootloader/encrypt.py https://raw.githubusercontent.com/kimd98/Docker-Builder/jetson_nano/encrypt.py && \
    cd linux-tegra-4.9  && \
    git checkout $HASH_COMMIT && \
    git reset --hard && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- tegra_defconfig && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs

# Generate dtb and dtb.encrypt using Gumstix AutoBSP and save in the shared folder
CMD cp /data/dts/devicetree-jetson_nano.dts /linux-tegra-4.9/nvidia/platform/t210/porg/kernel-dts/ && \
    sed -i '/makefile-path := /a dtb-y += devicetree-jetson_nano.dtb' /linux-tegra-4.9/nvidia/platform/t210/porg/kernel-dts/Makefile && \
    cd /linux-tegra-4.9 && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- tegra_defconfig && \
    make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs && \
    mkdir -p /data/dtb && \
    cp /linux-tegra-4.9/arch/arm64/boot/dts/_ddot_/_ddot_/_ddot_/_ddot_/nvidia/platform/t210/porg/kernel-dts/devicetree-jetson_nano.dtb /data/dtb/devicetree-jetson_nano.dtb && \
    mv /Linux_for_Tegra/kernel/dtb/tegra210-p3448-0002-p3449-0000-b00.dtb /Linux_for_Tegra/kernel/dtb/tegra210-p3448-0002-p3449-0000-b00.dtb.backup && \
    cp /linux-tegra-4.9/arch/arm64/boot/dts/_ddot_/_ddot_/_ddot_/_ddot_/nvidia/platform/t210/porg/kernel-dts/devicetree-jetson_nano.dtb /Linux_for_Tegra/kernel/dtb/kernel_tegra210-p3448-0002-p3449-0000-b00.dtb && \
    cd /Linux_for_Tegra/bootloader && \
    wget -O flash.xml https://raw.githubusercontent.com/kimd98/Docker-Builder/jetson_nano/NVIDIA/jetson-nano/flash.xml && \
    wget -O nvtboot.bin https://github.com/kimd98/Docker-Builder/raw/jetson_nano/NVIDIA/jetson-nano/nvtboot.bin && \
#    cp t210ref/cfg/flash_l4t_t210_emmc_p3448.xml flash.xml && \
#    cp t210ref/nvtboot.bin nvtboot.bin && \
    python3 encrypt.py ${VERSION}
    
