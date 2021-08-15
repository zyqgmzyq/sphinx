# qemu virtio-net

## virtio概述

很清晰：https://www.cnblogs.com/LoyenWang/p/14322824.html

## virtio-net
![image](https://user-images.githubusercontent.com/36949881/129468439-e7f91325-c959-422d-be91-ba21edff6b3f.png)

- 图中罗列了四个关键模块：`Virtio Device`、`Virtio Driver`、`Virtqueue`、`Notification（eventfd/irqfd）`；
- `Virtio Driver`：前端部分，处理用户请求，并将I/O请求转移到后端；
- `Virtio Device`：后端部分，由Qemu来实现，接收前端的I/O请求，并通过物理设备进行I/O操作；
- `Virtqueue`：中间层部分，用于数据的传输；
- `Notification`：交互方式，用于异步事件的通知；

https://www.cnblogs.com/LoyenWang/p/14399642.html

![image](https://user-images.githubusercontent.com/36949881/129468444-df718be1-d7d2-49c6-a30a-305d27e04097.png)

## virtio初始化
![image](https://user-images.githubusercontent.com/36949881/129468640-a14519d4-44a8-4118-b86e-5a6c2e7c069e.png)

图中与本文相关的有三个模块：1）模块初始化；2）网络设备初始化；3）设备初始化；

1. Qemu中设备模拟通过`type_init`先编译进系统，在`module_call_init`时进行回调，比如图中的`xxx_register_types`，在这些函数中都是根据`TypeInfo`类型信息来创建具体的实现信息；
2. `net_init_client`用来创建网络设备，比如`Tap`设备；
3. `device_init_func`根据Qemu命令的传入参数创建虚拟设备，比如`Virtio-Net`

## Tap创建

从上文中，我们知道，`Tap`与`Virtio-Net`属于前后端的关系，最终是通过结构体分别指向对方，如下图：
![image](https://user-images.githubusercontent.com/36949881/129468650-cdedf38a-2d8b-469d-84e1-56ac802bd7c9.png)


- `NetClientState`是网卡模拟的核心结构，表示网络设备中的几个端点，两个端点通过`peer`指向对方；

创建Tap设备的主要工作就是创建一个`NetClientState`结构，并添加到`net_clients`链表中：

![image](https://user-images.githubusercontent.com/36949881/129468658-cf9443de-4d49-40c4-b78a-2d2d0d5dc3d3.png)

先看qemu中的参数-netdev，创建了queues个TAPState，每个TAPState包含一个NetClientState，函数qemu_net_client_setup参数peer为空，所以创建的ncs中peer为空。

```c
main
    qemu_init
    	/* 解析netdev参数 */
    	net_client_parse(qemu_find_opts("netdev"), optarg) 
    	net_init_clients
			net_init_netdev     // netdev参数
    			net_client_init
    				net_client_init1
    					/*
    					 * 1. 根据tap的信息（script,queues等）来设置对应的值  然后对tap进行初始化
    					 * 2. 循环调用net_init_tap_one创建queues个TAPState，queues是传入的queues参数
    					 */
    					net_init_tap
    						fd = net_tap_init         // 获取fd,打开传入的ifname也就是tap0
    						net_init_tap_one          // 创建TAPState
    							net_tap_fd_init            
    								qemu_new_net_client
    									NetClientState *nc = g_malloc0(info->size);  // 创建NetClientState
    									qemu_net_client_setup(nc, info, peer, model, name, qemu_net_client_destructor);  // peer这里为NULL
	    				/* 根据netdev->id找到NetClientState，并设置nc->is_netdev为true */	
						nc = qemu_find_netdev(netdev->id);
						nc->is_netdev = true;
            net_param_nic	        // nic参数
            net_init_client			// net参数
```


然后可以看下qemu_net_client_setup函数，

```c
static void qemu_net_client_setup(NetClientState *nc,
                                  NetClientInfo *info,
                                  NetClientState *peer,
                                  const char *model,
                                  const char *name,
                                  NetClientDestructor *destructor)
{
    nc->info = info;    // 建立NetClientState到port的连接
    nc->model = g_strdup(model);
    if (name) {
        nc->name = g_strdup(name);
    } else {
        nc->name = assign_name(nc, model);
    }

    if (peer) {
        assert(!peer->peer);
        nc->peer = peer;
        peer->peer = nc;
    }
    QTAILQ_INSERT_TAIL(&net_clients, nc, next);       // 把nc(NetClientState)加入全局的net_clients链表中

    nc->incoming_queue = qemu_new_net_queue(qemu_deliver_packet_iov, nc);             // 设置接收队列
    nc->destructor = destructor;
    QTAILQ_INIT(&nc->filters);
}
```

函数的调用细节如下图：
![image](https://user-images.githubusercontent.com/36949881/129468673-1d0c9877-eec5-4dce-ac2e-0e3ad0f53b57.png)

- `net_tap_init`：与Host的`tun`驱动进行交互，其实质就是打开该设备文件，并进行相应的配置等；

- `net_tap_fd_init`：根据`net_tap_info`结构，创建`NetClientState`，并进行相关设置，这里边`net_tap_info`结构体中的接收函数指针用于实际的数据传输处理；

- `tap_read_poll`用于将fd添加到Qemu的AioContext中，用于异步响应，当有数据来临时，捕获事件并进行处理；

    以上就是Tap后端的创建过程，下文将针对前端创建了。

## virtio-net创建

### 数据结构

Qemu中用C语言实现了面向对象的模型，用于对设备进行抽象，精妙！
针对Virtio-Net设备，结构体及拓扑组织关系如下图：
![image](https://user-images.githubusercontent.com/36949881/129468678-eb7fd90e-76de-41eb-9ea5-b66e5ae5762f.png)

- `DeviceState`作为所有设备的父类，其中派生了`VirtIODevice`和`PCIDevice`，而本文研究的`Virtio-Net`派生自`VirtIODevice`；
- Qemu中会虚拟一个PCI总线，同时创建`virtio-net-pci`，`virtio-balloon-pci`，`virtio-scsi-pci`等PCI代理设备，这些代理设备挂载在PCI总线上，同时会创建Virtio总线，用于挂载最终的设备，比如`VirtIONet`；
- PCI代理设备就是一个纽带；

### 流程分析

与设备创建相关的三个函数，可以从`device_init_func`入口跟踪得知：
![image](https://user-images.githubusercontent.com/36949881/129468684-75d028bd-360f-4f4c-9489-6ed60e0aa573.png)

- 当Qemu命令通过`-device`传入参数时，`device_init_func`会根据参数去查找设备，并最终调用到该设备对应的类初始化函数、对象初始化函数、以及realize函数；
- 所以，我们的分析就是这三个入口；

#### class_init
![image](https://user-images.githubusercontent.com/36949881/129468694-cc786f85-6e48-4dbe-a167-26e877f229db.png)
- 在网卡虚拟化过程中，参数只需要指定PCI代理设备即可，也就是`-device virtio-net-pci, netdev=tap0`，从而会调用到`virtio_net_pci_class_init`函数；如果指定`-device virtio-net-device, netdev=tap0`,就会调用到`virtio_net_class_init`函数
- 由于实现了类的继承关系，在子类初始化之前，需要先调用父类的实现，图中也表明了继承关系以及调用函数顺序；
- C语言实现继承，也就是将父对象放置在自己结构体的开始位置，图中的颜色能看出来；

#### instance_init

类初始化结束后，开始对象的创建：
![image](https://user-images.githubusercontent.com/36949881/129468703-1b65976c-6997-4691-ac2d-c34db67dcda0.png)

- 针对`Virtio-Net-PCI`的实例化比较简单，作为代理，负责将它的后继对象初始化，也就是本文的前端设备`Virtio-Net`；
- 针对virtio-net-device的实例化直接调用virtio_net_instance_init即可；

#### realize

- `realize`的调用，比较绕，简单来说，它的类继承关系中存在多个`realize`的函数指针，最终会从父类开始执行，一直调用到子类，而这些函数指针的初始化在什么时候做的呢？没错，就是在class_init类初始化的时候，进行了赋值；
- virtio-net-pci左边图所示
- virtio-net-device右边图所示
![image](https://user-images.githubusercontent.com/36949881/129468708-7b01614a-3eab-4685-a5d9-0cfa0642638c.png)

```c
 qemu_init
	device_init_func
		/* 会find driver，类型为 virtio-net-device */
		qdev_device_add
    		dev = qdev_new(driver);                    // 创建设备
    		qdev_realize(DEVICE(dev), bus, errp)       // 实现设备
                object_property_set_bool
                	object_property_set_qobject	
                		object_property_set
                			property_set_bool
                				device_set_realized
                					virtio_pci_dc_realize
                						pci_qdev_realize
                							virtio_pci_realize
                								virtio_net_pci_realize
                									qdev_realize(vdev, BUS(&vpci_dev->bus), errp);
														object_property_set_bool	
                                                            object_property_set_qobject
                                                            	property_set_bool
                                                            		device_set_realized
                                                            			virtio_device_realize
                                                            				virtio_net_device_realize
                                                            					qemu_new_nic
                                                            						/* 循环调用qemu_net_client_setup设置queues个TAPState，queues是传入的queues参数 */
                                                            						qemu_net_client_setup // 和tap init相比，peer不为NULL，是tap的NetClientState
```

### virtio_net_device_realize

- `virtio_net_pci_realize`函数，会触发`virtio_device_realize`的调用，该函数是一个通用的virtio设备实现函数，所有的virtio设备都会调用，而我们的前端设备`Virtio-Net`也是virtio设备；
- `virtio_net_device_realize`就到了我们的主角了，它进行了virtio通用的设置（后续在数据通信中再分析），还创建了一个`NetClientState`端点，与`Tap`设备对应，分别指向了对方，惺惺相惜，各自安好；
- `virtio_bus_device_plugged`表示设备插入总线时的处理，完成的工作就是按照PCI总线规划，配置各类信息，以便与Guest OS中的virtio驱动交互，后续的文章再分析了；

本文基本捋清了虚拟网卡前端设备和后端设备的创建过程，完成的工作只是绑定了彼此，数据交互以及通知机制，留给后续吧。
![image](https://user-images.githubusercontent.com/36949881/129468719-05cdc595-4312-4049-a80e-fe84649030c1.png)

```c
virtio_device_realize
    virtio_net_device_realize
        virtio_init
        virtio_net_add_queue
            virtio_add_queue  // rx和tx的handle_output分别是virtio_net_handle_rx和virtio_net_handle_tx_bh
        virtio_add_queue      // 控制qemu是virtio_net_handle_ctrl
    	qemu_new_nic          // 创建NetClientState，与tap对应,  peer和tap的peer互相指向
    virtio_bus_device_plugged
```

## Virtio Driver
https://www.cnblogs.com/LoyenWang/p/14444344.html

## Virtio Queue

https://www.cnblogs.com/LoyenWang/p/14589296.html



guest把分配的vring地址传递给qemu

```javascript
virtio_pci_common_write
  └─virtio_queue_set_rings
      └─virtio_init_region_cache
          └─address_space_cache_init//这个函数等qemu内存虚拟化时一块分析
```

给kvm注册一个eventfd，等guest kick时，kvm通知qemu进程

```javascript
virtio_pci_common_write
  └─virtio_pci_start_ioeventfd
      └─virtio_bus_start_ioeventfd
          └─virtio_device_start_ioeventfd_impl
              ├─virtio_bus_set_host_notifier
              |   └─virtio_pci_ioeventfd_assign
              |       └─memory_region_add_eventfd
              └─event_notifier_set_handler(virtio_queue_host_notifier_read)
```

guest里的virtio-net通知tx或者rx写mmio，带着vector号，kvm通知qemu

```javascript
virtio_pci_notify_write
  └─virtio_queue_notify
      ├─handle_output
      └─event_notifier_set
virtio_queue_host_notifier_read
  └─virtio_queue_notify_vq
      └─handle_output
```

不管是发送还是接收，都是guest设置好vring中的address，是guest的physical address，需要qemu调用address_space_map转换成自己的virtual address。

收发包的原理就是tap收到发往guest，从guest收到发往tap，tap和virtio-net-pci peer互相指，从自己NetClientState的peer找到对端的NetClientState，然后找到NetClientState中的incoming_queue，incoming_queue中deliver调用receive函数。

qemu读tap，然后调用virtio_net_receive，如果virtio_net_receive不能receive，等guest kick时再用virtio_net_handle_rx收包。

```javascript
tap_send
  └─qemu_send_packet_async
      └─qemu_send_packet_async_with_flags
          └─qemu_net_queue_send
              └─调用到virtio-net的virtio_net_receive
```

guest kick时接收，virtio_net_handle_rx is handle_outpu，rxvq是VRING_DESC_F_WRITE，DMA_DIRECTION_FROM_DEVICE，站在guest角度看问题，从qemu到guest内存

```javascript
virtio_net_handle_rx
  └─qemu_flush_queued_packets
      └─qemu_flush_or_purge_queued_packets
          └─qemu_net_queue_flush
              └─qemu_net_queue_deliver
                  └─qemu_deliver_packet_iov
                      └─nc_sendv_compat
                          └─virtio_net_receive

virtio_net_receive_rcu
  ├─virtio_net_process_rss选择接收的queue
  |   └─virtqueue_pop
  |       └─virtqueue_split_pop
  |           └─virtqueue_map_desc
  |               └─dma_memory_map
  |                   └─address_space_map
  ├─virtqueue_fill
  ├─virtqueue_flush
  └─virtio_notify
```

guest kick时发送virtio_net_handle_tx_bh is handle_output

```javascript
#guest kick时发送virtio_net_handle_tx_bh is handle_output
virtio_net_handle_tx_bh
  └─virtio_net_tx_bh
      ├─virtio_net_flush_tx
      |   ├─virtqueue_pop
      |   |   └─virtqueue_split_pop
      |   |       └─virtqueue_map_desc
      |   |           └─dma_memory_map
      |   |               └─address_space_map
      |   ├─qemu_sendv_packet_async
      |   |   └─qemu_net_queue_send_iov
      |   |       └─qemu_net_queue_deliver_iov
      |   |           └─qemu_deliver_packet_iov
      |   |               └─调用到了对端的peer_receive就是tap_receive
      |   |                  └─tap_write_packet
      |   └─qemu_net_queue_flush
      |       └─qemu_net_queue_deliver
      └─bh的回调函数virtio_net_tx_complete
          ├─virtqueue_push
          |    ├─virtqueue_fill
          |    └─virtqueue_flush
          |        └─vring_used_idx_set
          └─virtio_notify
```

记录dirty page用于live migration

```javascript
virtqueue_fill
  ├─virtqueue_unmap_sg
  |   └─dma_memory_unmap
  |       └─address_space_unmap
  |           └─invalidate_and_set_dirty
  └─virtqueue_split_fill
      └─vring_used_write
          └─address_space_write_cached
              ├─flatview_write_continue
              |   └─invalidate_and_set_dirty
              └─address_space_cache_invalidate
```
