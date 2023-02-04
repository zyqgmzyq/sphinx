# Qemu Debug

## 直接用gdb运行QEMU   

```c
gdb-multiarch -tui -args qemu-system-aarch64 -machine gic-version=3,iommu=smmuv3 -machine virtualization=true -cpu cortex-a72 -machine type=virt -m 3G -smp 8 -kernel Image -nographic -initrd rootfs.img.gz -append "rw root=/dev/ram rdinit=/sbin/init earlyprintk=serial,ttyAMA0 console=ttyAMA0"

start
```

## 使用gdb的remote debug

先在一个终端中进入qemu-system-aarch64所在目录，然后运行gdb server

```
gdbserver --multi 127.0.0.1:1234
```

在另一个终端中启动gdb，注意参数中引号前的“\”

```
gdb-multiarch -tui -args qemu-system-aarch64 -machine gic-version=3,iommu=smmuv3 -machine virtualization=true -cpu cortex-a72 -machine type=virt -m 3G -smp 8 -kernel Image -nographic -initrd rootfs.img.gz -append "rw root=/dev/ram rdinit=/sbin/init earlyprintk=serial,ttyAMA0 console=ttyAMA0"
```

再在gdb中键入如下内容

```
target extended-remote 127.0.0.1:1234
set remote exec-file ./qemu-system-aarch64
start                                    
```
