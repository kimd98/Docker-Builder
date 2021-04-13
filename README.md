# docker-builder

## Raspberry Pi Compute Module 4 (64-bit)

1. Install required dependencies and the 64-bit toolchain for a 64-bit kernel
```
sudo apt install git bc bison flex libssl-dev make libc6-dev libncurses5-dev
sudo apt install crossbuild-essential-arm64
```

2. Get sources
```
git clone --depth=1 https://github.com/raspberrypi/linux
```

3. 64-bit configs for CM4
```
cd linux
KERNEL=kernel8
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- bcm2711_defconfig
```

4. 64-bit build with configs
```
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs
```
