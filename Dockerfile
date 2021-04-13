FROM ubuntu:20.04

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
    crossbuild-essential-arm64

# Get the source code
RUN git clone --depth=1 https://github.com/raspberrypi/linux
WORKDIR /linux

# 64-bit configs for CM4
RUN KERNEL=kernel8
RUN make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig

# 64-bit build with configs
# Speed up compilation on multiprocessor systems
RUN make -j 3 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs

# Process done
CMD [“echo”,”CM4 Docker Image”] 
