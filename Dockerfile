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
    crossbuild-essential-arm64

# Get the source code & 64-bit build with configs for CM4
RUN git clone --depth=1 https://github.com/raspberrypi/linux && \
    cd linux && \
    KERNEL=kernel8 && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig && \
    make -j 4 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs

# Process done
CMD [“echo”,”CM4 Docker Image”]
