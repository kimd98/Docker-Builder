## Quick Start 

**DEPRECATED** PLEASE CHECK OUT 'jetson' BRANCH for JETSON NANO!

1. Make a shared folder **data-jetson** on the host computer (only for initial use)
```
  $ mkdir ~/data-jetson
```
2. Place the AutoBSP dts file in the shared folder **dts subfolder**
```
  $ cp path/to/AutoBSP/devicetree-jetson_nano.dts ~/data-jetson/dts/
```
3. Build a docker container (Please remember to assign the correct board to the variable VERSION!)

   **[option 1]** Get a docker image from DockerHub
    ```
    $ docker run  -it --rm -v ~/data-jetson:/data -e VERSION='jetson-nano' 'gumstix2021lena/docker-builder:jetson_nano 
    ```

   **[option 2]** Build locally
    ```
    $ git clone -b jetson_nano https://github.com/kimd98/Docker-Builder.git
    $ cd Docker-Builder
    $ docker build -t docker-builder:jetson_nano .
    $ docker run  -it --rm -v ~/data-jetson:/data -e VERSION='jetson-nano' docker-builder:jetson_nano
    ```

4. Check the **dtb subfolder** to see dtb and dtb.encrypt files
```
  $ ls ~/data-jetson/dtb
```
