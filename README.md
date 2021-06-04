## Quick Start 
1. Make a shared folder **data-jetson** on the host computer (only for initial use)
```
  $ mkdir ~/data-jetson
```
2. Place the AutoBSP dts file in the shared folder **dts subfolder**
```
  $ cp path/to/AutoBSP/devicetree-jetson.dts ~/data-jetson/dts/
```
3. Build a docker container (Please remember to assign the correct board to the variable VERSION!)

   **[option 1]** Get a docker image from DockerHub
    ```
    $ docker run  -it --rm -v ~/data-jetson:/data -e VERSION='tx2' 'gumstix2021lena/docker-builder:jetson 
    ```

   **[option 2]** Build locally
    ```
    $ git clone -b jetson_nano https://github.com/kimd98/Docker-Builder.git
    $ cd Docker-Builder
    $ docker build -t docker-builder:jetson .
    $ docker run  -it --rm -v ~/data-jetson:/data -e VERSION='tx2' docker-builder:jetson
    ```
    
    VERSION: 'nano', 'tx2', 'xavier'

4. Check the **dtb subfolder** to see the dtb file
```
  $ ls ~/data-jetson/dtb
```
   - TX2: devicetree-jetson_tx2.dtb

5. Check the **signed subfolder** to see the dtb.encrypt file
```
  $ ls ~/data-jetson/signed
```
   - TX2: tegra186-quill-p3489-0888-a00-00-base_sigheader.dtb.encrypt
