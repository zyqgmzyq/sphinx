# VIRTIO CAN

```shell
# qemu命令
-object can-bus,id=canbus0 -device virtio-can-device,canbus=canbus0 -object can-host-socketcan,id=canhost0,if=vcan0,canbus=canbus0

# host添加vcan设备
sudo insmod /lib/modules/`uname -r`/kernel/drivers/net/can/vcan.ko
sudo ip link add type vcan
ip link set up vcan0

# guest 打开can设备
ip link set can0 up type can bitrate 125000

# guest 监听
candump can0
# guset 发送
cansend can0 0x11 0x22 0x33 0x77 0x24 0x89 0x52

# host 发送
cansend vcan0 5A1#11.2233.44556677.88

# guest和host都要安装can-utils工具
guest os的can-utils工具放在aos_virt/bin目录下了,直接用就可以
```



## 参考

[IO设备管理-virtio mmio](https://rcore-os.github.io/rCore-Tutorial-Book-v3/chapter8/1io-interface.html)

[Virtio Spec Overview](https://kernelgo.org/virtio-overview.html)

## QEMU 新增 VIRTIO-CAN DEVICE

### 添加文件

```c
/* hw/net/can/meson.build添加 */
softmmu_ss.add(when: 'CONFIG_VIRTIO_CAN', if_true: files('virtio-can.c'))

/* hw/net/Kconfig添加 */    
config VIRTIO_CAN
    bool
    default y
    select VIRTIO
```

### 添加设备

include/standard-headers/linux/virtio_ids.h文件中添加新的virtio设备

```c
#define VIRTIO_ID_CAN          21 /* virtio can */
```

hw/virtio/virtio.c文件中添加新设别

```c
virtio_legacy_allowed(VirtIODevice *vdev)
{
    switch (vdev->device_id) {
    case VIRTIO_ID_NET:
    case VIRTIO_ID_CAN:  /* 添加virtio can设备*/
    case VIRTIO_ID_BLOCK:
	......
        return true;
    default:
        return false;
    }
}

```



## linux内核增加VIRTIO-CAN驱动

### Kconfig文件配置

`Kconfig`文件是`menuconfig`的关键文件。Kconfig用来配置内核，它就是各种配置界面的源文件，内核的配置工具读取各个Kconfig文件，生成配置界面供开发人员配置内核，最后生成配置文件.config

can的Kconfig文件在drivers/net/can/Kconfig,添加以下内容

```shell
config VIRTIO_CAN
	tristate "Virtio can driver"
	depends on VIRTIO
	---help---
	  This is the virtual can driver for virtio.  It can be used with
	  QEMU based VMMs (like KVM or Xen).  Say Y or M.
```

### Makefile文件修改

找到对应的Makefile文件加入自己的文件，这里修改的是drivers/net/can/Makefile

```shell
obj-$(CONFIG_VIRTIO_CAN)       += virtio_can.o
```

### virtio_can driver

在include/uapi/linux/virtio_ids.h文件中添加新的virtio设备

```c
#define VIRTIO_ID_CAN          21 /* virtio can */
```

### 内核编译打开对应的config

```shell
CONFIG_CAN=y
CONFIG_VIRTIO_CAN=y
```



## QEMU VIRTIO-CAN DEVICE初始化

![image-20210701110702168](01-virtio-can.assets/image-20210701110702168.png)

1. Qemu中设备模拟通过`type_init`先编译进系统，在`module_call_init`时进行回调，比如virtio_register_type

2. 调用module_call_init(type) 时，找到virtio_can_info对应的init函数开始执行这里是调用virtio_can_class_init函数；

3. qemu_opts_parse_noisily(qemu_find_opts("object"),optarg, true)解析object参数；

4. `device_init_func`根据Qemu命令的传入参数创建虚拟设备virtio-can

    - 调用virtio_can_instance_init函数创建virtio can device设备；
    -     
    - 调用virtio_can_device_realize函数
    - 
    
    ```c
    static void virtio_can_device_realize(DeviceState *dev, Error **errp)
    {
        VirtIODevice *vdev = VIRTIO_DEVICE(dev);
        VirtIOCan *vcan = VIRTIO_CAN(dev);
        size_t config_size = sizeof(struct virtio_can_config);
    
        virtio_add_feature(&vcan->host_features, VIRTIO_CAN_F_CTRL_VQ);  
        virtio_init(vdev, "virtio-can", VIRTIO_ID_CAN, config_size);            /* 初始化virtio-can设备 */
    
        vcan->ctrl_vq = virtio_add_queue(vdev, 64, virtio_can_handle_ctrl);     /* 添加ctrl queue，并设置ctrl queue的handle函数 */
    
        vcan->bus_client.info = &can_virtio_bus_client_info; 
        can_bus_insert_client(vcan->canbus, &vcan->bus_client);                 /* 把创建的canbusclient插入到canbus链表中 */
    }
    ```

## Linux Driver 

### 数据结构


### virtio总线创建


### Driver Probe

`bus_register`注册virtio总线，总线负责匹配；linux在init_call过程中会调用到virtio_can_driver_init函数注册virtio_can_driver,注册过程中总线会负责匹配；
![image-20210628094651030](01-virtio-can.assets/image-20210628094651030.png)

在匹配成功后调用通用的`virtio_dev_probe`函数；


`virtio_dev_probe`函数里会去调用实际的probe函数

```c
virtio_dev_probe
	drv->probe(dev)
		virtcan_probe
			init_vqs                  /* 初始化virt queue  */
    			virtio_find_vqs
   			register_candev(dev);     /* 注册can设备 */
			virtio_device_ready       /* enable vq use */
```

![image](https://user-images.githubusercontent.com/36949881/142763760-ac6ea374-9f1f-4d2a-be55-1ac6d01a147f.png)








