## Quick Start 
1. Make a shared folder **data-jetson_nano** on the host computer (only for initial use)
```
  $ mkdir ~/data-jetson_nano
```
2. Place the AutoBSP dts file in the shared folder **dts subfolder**
```
  $ cp path/to/AutoBSP/devicetree-jetson_nano.dts ~/data-jetson_nano/dts/
```
3. Build a docker container

   **[option 1]** Get a docker image from DockerHub
    ```
    $ docker run  -it --rm -v ~/data-jetson_nano:/data gumstix2021lena/docker-builder:jetson_nano 
    ```

   **[option 2]** Build locally
    ```
    $ git clone -b jetson_nano https://github.com/kimd98/Docker-Builder.git
    $ cd Docker-Builder
    $ docker build -t docker-builder:jetson_nano .
    $ docker run  -it --rm -v ~/data-jetson_nano:/data docker-builder:jetson_nano
    ```

4. Check the **dtbo subfolder** to see a generated dtbo file
```
  $ ls ~/data-jetson_nano/dtbo
```
