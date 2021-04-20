# docker-builder

## Quick Start 
1. Make a shared folder **docker-data** (only for initial use)
```
  $ mkdir ~/docker-data
```
2. Place the AutoBSP dts file in the shared folder **dts subfolder**
```
  $ cp path/to/AutoBSP/upverter-overlay.dts ~/docker-data/dts/
```
3. Build a docker container

   **[option 1]** Get a docker image from DockerHub
```
    $ docker run  -it --rm -v ~/docker-data:/data gumstix2021lena/docker-builder:main
```
   **[Option 2]** Build locally
```
    $ git clone https://github.com/kimd98/docker-builder.git
    $ cd docker-builder
    $ docker build -t docker-builder .
    $ docker run  -it --rm -v ~/docker-data:/data docker-builder
```

4. Check the **dtbo subfolder** to see a generated dtbo file
```
  $ ls ~/docker-data/dtbo
```
