# 编译并运行Qemu
## Qemu的编译

```shell
./configure --target-list=x86_64-softmmu,x86_64-linux-user,arm-softmmu,arm-linux-user,aarch64-softmmu,aarch64-linux-user --enable-kvm --enable-sdl --enable-debug --enable-debug-stack-usage --enable-sdl --enable-opengl 

make && make install
```

## Kernel的编译

```shell
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
make -j4 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-

# linux-stable编译
make CROSS_COMPILE=aarch64-linux-gnu- -j8
```

## Qemu拉起Linux

```shell
qemu-system-aarch64 -machine its,gic-version=3,iommu=smmuv3,virtualization=true,type=virt -cpu cortex-a72 -m 4G -smp 8 -kernel Image -nographic -initrd rootfs.img.gz -append "rw root=/dev/ram rdinit=/sbin/init earlyprintk=serial,ttyAMA0 console=ttyAMA0" -chardev socket,id=qemu-monitor,host=localhost,port=7777,server=on,wait=off,telnet=on -mon qemu-monitor,mode=readline
```

增加虚拟设备磁盘，先使用initrd作为临时文件系统然后再mount磁盘

```shell
qemu-system-aarch64 -machine gic-version=3,iommu=smmuv3 -machine virtualization=true -cpu cortex-a72 -machine type=virt -m 2048 -smp 8 -kernel Image -nographic -initrd rootfs.img.gz -append "rw root=/dev/ram rdinit=/sbin/init earlyprintk=serial,ttyAMA0 console=ttyAMA0" -drive file=sysDrv_rootfs.ext4,if=none,format=raw,id=hd0 -device virtio-blk-device,drive=hd -chardev socket,id=qemu-monitor,host=localhost,port=7777,server=on,wait=off,telnet=on -mon qemu-monitor,mode=readline
```

## GDB调试kernel

```shell
gdb-multiarch vmlinux
set architecture aarch64
target remote :1234
然后就可以gdb调试了

```

## 生成Qemu的dtb

```shell
qemu-system-aarch64 -machine its,gic-version=3,iommu=smmuv3,virtualization=true,type=virt -cpu cortex-a72 -m 4G -smp 8 -display none -machine dumpdtb=virt-gicv3.dtb
```

## 网络配置

```shell
# briage网络
# host创建虚拟网卡
sudo brctl addbr br0
sudo tunctl -t tap0 -u `whoami`
sudo brctl addif br0 tap0
sudo ifconfig tap0 up
sudo ifconfig br0 192.168.1.1/24 up
sudo brctl showstp br0

-netdev type=tap,id=net0,script=no,downscript=no,ifname=tap0 -device virtio-net,netdev=net0

# user网络（NAT）
-netdev user,id=eth0 -device virtio-net-device,netdev=eth0
```

## 磁盘blk配置
```
-drive file=sysDrv_rootfs.ext4,if=none,format=raw,id=hd0 -device virtio-blk-device,drive=hd0
```

## numa节点配置

```c
-object memory-backend-ram,id=mem0,size=2G -object memory-backend-ram,id=mem1,size=2G -numa node,memdev=mem0,cpus=0-3 -numa node,memdev=mem1,cpus=4-7
```

### telnet端口

```
-serial tcp::5000,server,nowait
```

