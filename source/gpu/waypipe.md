# waypipe

### 挂载qcow2格式磁盘

https://blog.csdn.net/wllabs/article/details/87866802?utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7EBlogCommendFromMachineLearnPai2%7Edefault-13.control&dist_request_id=&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7EBlogCommendFromMachineLearnPai2%7Edefault-13.control

```shell
sudo guestmount -a aos_template_wl.qcow2 -m /dev/sda2 tmp
sudo guestunmount tmp
```

### 使用qcow2磁盘拉起

```shell
qemu-system-aarch64 -cpu cortex-a72 -machine type=virt -smp 8 -kernel Image -snapshot -hda aos_template_wl.qcow2 -append "rw root=/dev/vda2 rootfstype=ext4 earlyprintk=serial,ttyAMA0 console=ttyAMA0" -nographic -m 4G -device virtio-gpu-pci  -display sdl,gl=on  -netdev user,id=eth0  -device virtio-net-device,netdev=eth0 -netdev type=tap,id=net0,script=no,downscript=no,ifname=tap0 -device virtio-net,netdev=net0
```

### 修改/etc/ssh/sshd_config

一开始连接时候总是报错  说remote port forwarding failed, 网络都还给老师了，一窍不通。

![image](https://user-images.githubusercontent.com/36949881/116170004-810c3480-a738-11eb-8fbc-d09b7e5381a3.png)

然后我以为是这个机器网络配置啥的有问题，所以就去tx2上装了一下waypipe试了下，tx2上ok.

对比了一下/etc/ssh/sshd_config文件，发现sshd里面多了这一大串，感觉像是一些通信算法啥的，感觉可能是这一大串影响了waypipe ssh时候创建socket。

所以把这一些都删掉就不再报remote port forwarding failed的错误了，具体这些事干啥的还不清楚 。
![image](https://user-images.githubusercontent.com/36949881/116170019-87021580-a738-11eb-9659-e49c779ba57a.png)




## 修改~/.bashrc

添加这两行,这个是设置环境变量
![image](https://user-images.githubusercontent.com/36949881/116170050-997c4f00-a738-11eb-9d0c-7f2f77183de9.png)


```shell
mkdir /tmp/way
chmod 0700 /tmp/way
```



### 运行waypipe

```shell
waypipe ssh 192.168.1.5 weston
```

