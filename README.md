## Quick Start 
1. Make a shared folder (only for initial use)
```
  $ mkdir ~/data-rpi_cm4
```
2. Place the AutoBSP dts file in the shared folder **dts subfolder**
```
  $ cp path/to/AutoBSP/upverter-overlay.dts ~/data-rpi_cm4/dts/
```
3. Build a docker container

   **[option 1]** Get a docker image from DockerHub
    ```
    $ docker run  -it --rm -v ~/data-rpi_cm4:/data gumstix2021lena/docker-builder:rpi_cm4
    ```

   **[option 2]** Build locally
    ```
    $ git clone -b rpi_cm4 https://github.com/kimd98/Docker-Builder.git
    $ cd Docker-Builder
    $ docker build -t docker-builder:rpi_cm4 .
    $ docker run  -it --rm -v ~/data-rpi_cm4:/data docker-builder:rpi_cm4
    ```

4. Check the **dtbo subfolder** to see a generated dtbo file
```
  $ ls ~/data-rpi_cm4/dtbo
```
