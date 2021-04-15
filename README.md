# docker-builder

## Raspberry Pi Compute Module 4 (64-bit) - Dockerfile

1. Install required dependencies and the 64-bit toolchain for a 64-bit kernel
```
  $ sudo apt install git bc bison flex libssl-dev make libc6-dev libncurses5-dev
  $ sudo apt install crossbuild-essential-arm64
  $ apt-get install device-tree-compiler nano
```
2. Get sources
```
  $ git clone --depth=1 https://github.com/raspberrypi/linux
```
3. 64-bit configs for CM4
```
  $ cd linux
  $ KERNEL=kernel8
  $ make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig
```
4. 64-bit build with configs
```
  $ make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs
```

## Docker Commands

1. Build an image locally (optional)
```
  $ git clone https://github.com/kimd98/docker-builder.git
  $ cd docker-builder
  $ docker build .
```

2. Create a shared folder on host and copy AutoBSP
```
  $ mkdir ~/docker-data
  $ sudo cp <AutoBSP filepath> ~/docker-data/
```
   - shared folder "docker data" created on host computer

3. Run a docker container from DockerHub
```
  $ docker run  -dit -P --name docker-data -v ~/docker-data:/data gumstix2021lena/docker-builder:main
```
   - docker container name: docker-data

4. Access to the container
```
  $ docker attach docker-data
```
   - To restart the container, type `docker start -a docker-data`
   - To find a container ID, type `docker ps -a`
   - To see the AutoBSP folder, type `ls /data/`

5. Copy dts file to linux kernel overlays folder
```
  # cp /data/rpi_cm4_0/upverter-overlay.dts linux/arch/arm64/boot/dts/overlays/
```
6. Compile dts to dtbo
```
  # cd /linux/arch/arm64/boot/dts/overlays
  # dtc -I dts -O dtb -o upverter.dtbo upverter-overlay.dts
```
7. Kernel Cross-compilation (only dtbs)
```
  # cd /linux
  # KERNEL=kernel8
  # make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig
  # make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs
```
