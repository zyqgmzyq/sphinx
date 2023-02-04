# qemu virtio-gpu

## Host os 

### 安装依赖

```shell
sudo apt-get install libglib2.0-dev ninja-build build-essential libepoxy-dev libdrm-dev libgbm-dev libvirglrenderer-dev libpulse-dev libsdl2-dev xwayland libx11-dev libpixman-1-dev
```

### Qemu编译

```shell
./configure --target-list=aarch64-softmmu,x86_64-softmmu,aarch64-linux-user --enable-sdl --enable-debug --enable-opengl --enable-virglrenderer --enable-kvm

make && make install
```

### 创建uefi固件、块设备

```shell
dd if=/dev/zero of=flash0.img bs=1M count=64
wget http://releases.linaro.org/15.01/components/kernel/uefi-linaro/release/qemu64-intelbds/QEMU_EFI.fd
dd if=QEMU_EFI.fd of=flash0.img conv=notrunc
dd if=/dev/zero of=flash1.img bs=1M count=64
dd if=/dev/zero of=hda.img bs=1M count=10240
```

### 安装Mesa

```shell
git clone https://anongit.freedesktop.org/git/mesa/mesa.git

mkdir build
cd build
meson ..
```

### 下载ubuntu image

```shell
wget https://cdimage.ubuntu.com/focal/daily-live/current/focal-desktop-arm64.iso
```

### 运行启动虚拟机脚本拉起guest os

```shell
#!/bin/sh

CDROM_IMG=ubuntu-18.04.5-server-arm64.iso
HDA_IMG=hda.img

make_cdrom_arg()
{
  echo "-drive file=$1,id=cdrom,if=none,media=cdrom" \
    "-device virtio-scsi-device -device scsi-cd,drive=cdrom"
}

make_hda_arg()
{
  echo "-drive if=none,file=$1,id=hd0" \
    "-device virtio-blk-device,drive=hd0"
}

HDA_ARGS=`make_hda_arg $HDA_IMG`
if [ $# -eq 1 ]; then
  case $1 in
    install)
      CDROM_ARGS=`make_cdrom_arg $CDROM_IMG`
      ;;
    *)
      CDROM_ARGS=""
      ;;
  esac
fi

qemu-system-aarch64 -m 1024 -cpu cortex-a72 -M virt  -nographic \
  -pflash flash0.img \
  $CDROM_ARGS \
  $HDA_ARGS \
  -netdev user,id=eth0 \
  -device virtio-net-device,netdev=eth0  -device virtio-gpu-pci \
  -display sdl.gl=on \
  -device usb-ehci,id=ehci \
  -machine usb=on \
  -k en-us \
  -device usb-mouse \
  -device usb-kbd -show-cursor=on
```



## Guest os

### 查看是否有virtio-gpu

```shell
lspci
```
![image](https://user-images.githubusercontent.com/36949881/116170080-ac8f1f00-a738-11eb-9e59-29e183a4aa6f.png)


### 安装meson

```shell
pip3 install --user meson
```

### 安装wayland

```shell
# 依赖包要先装一下
apt-get install libffi-dev libxml2-dev dot2tex doxygen xsltproc xmlto ninja-build

git clone https://gitlab.freedesktop.org/wayland/wayland.git
cd wayland
meson build/ --prefix=/usr
ninja -C build/ install
cd ..
```

### 安装Wayland protocols

```shell
git clone https://gitlab.freedesktop.org/wayland/wayland-protocols.git
cd wayland-protocols
meson build/ --prefix=/usr
ninja -C build/ install
cd ..
```

### 安装Weston 

```shell
# 依赖包要先装一下
sudo apt-get install libxkbcommon-x11-dev libpixman-1-dev libinput-dev libdrm-dev libcairo2-dev libjpeg-dev libwebp-dev libegl1-mesa-dev libsystemd-dev libpam0g-dev libgles2-mesa-dev libgbm-dev libva-dev freerdp2-dev libxcb-composite0-dev libxcursor-dev liblcms2-dev libcolord-dev libgstreamer1.0-dev libgstreamermm-1.0-dev

git clone https://gitlab.freedesktop.org/wayland/weston.git
cd weston
meson build/ --prefix=/usr
ninja -C build/ install
cd ..
```

### 安装mesa

```shell
git clone https://anongit.freedesktop.org/git/mesa/mesa.git
mkdir build
cd build
meson ..

cd ..
ninja -C build/ install
```

可能遇到得错误

-  llvm not fount

  `sudo apt-get install llvm`

-  libdrm_nouveau 版本过低 ，从<http://dri.freedesktop.org/libdrm/> 下载drm最新源码 重新编译libdrm

- byacc not found

  `sudo apt-get install byacc`

- flex not found

  `sudo apt-get install flex`
  
- xrandr not found
  
  `sudo apt-get install libxrandr-dev`

### 安装简易桌面

```shell
sudo apt-get install x-window-system-core
```

