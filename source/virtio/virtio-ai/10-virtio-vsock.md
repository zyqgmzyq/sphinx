# virtio-vsock

## Qemu侧代码

### vhost_vsock_class_init

```c
static void vhost_vsock_class_init(ObjectClass *klass, void *data)
{
    DeviceClass *dc = DEVICE_CLASS(klass);
    VirtioDeviceClass *vdc = VIRTIO_DEVICE_CLASS(klass);    

    device_class_set_props(dc, vhost_vsock_properties);      /* 设置properties （guest-cid / vhostfd） */
    dc->vmsd = &vmstate_virtio_vhost_vsock;                  /* 设置一系列回调函数 */
    vdc->realize = vhost_vsock_device_realize;
    vdc->unrealize = vhost_vsock_device_unrealize;
    vdc->get_features = vhost_vsock_get_features;
    vdc->get_config = vhost_vsock_get_config;
    vdc->set_status = vhost_vsock_set_status;
}
```



### vhost_vsock_device_realize  

```c
static void vhost_vsock_device_realize(DeviceState *dev, Error **errp)
{
    VHostVSockCommon *vvc = VHOST_VSOCK_COMMON(dev);
    VirtIODevice *vdev = VIRTIO_DEVICE(dev);
    VHostVSock *vsock = VHOST_VSOCK(dev);
    int vhostfd;
    int ret;

    /* Refuse to use reserved CID numbers */
    if (vsock->conf.guest_cid <= 2) {
        error_setg(errp, "guest-cid property must be greater than 2");
        return;
    }

    if (vsock->conf.guest_cid > UINT32_MAX) {
        error_setg(errp, "guest-cid property must be a 32-bit number");
        return;
    }

    if (vsock->conf.vhostfd) {
        vhostfd = monitor_fd_param(monitor_cur(), vsock->conf.vhostfd, errp);
        if (vhostfd == -1) {
            error_prepend(errp, "vhost-vsock: unable to parse vhostfd: ");
            return;
        }

        ret = qemu_try_set_nonblock(vhostfd);
        if (ret < 0) {
            error_setg_errno(errp, -ret,
                             "vhost-vsock: unable to set non-blocking mode");
            return;
        }
    } else {
        vhostfd = open("/dev/vhost-vsock", O_RDWR);                           /* 打开vhost-vsock设备*/
        if (vhostfd < 0) {
            error_setg_errno(errp, errno,
                             "vhost-vsock: failed to open vhost device");
            return;
        }

        qemu_set_nonblock(vhostfd);
    }

    vhost_vsock_common_realize(vdev, "vhost-vsock");                        /* vhost-vsock realize */

    ret = vhost_dev_init(&vvc->vhost_dev, (void *)(uintptr_t)vhostfd,       /* 初始化vhost-vsock设备 */
                         VHOST_BACKEND_TYPE_KERNEL, 0);
    if (ret < 0) {
        error_setg_errno(errp, -ret, "vhost-vsock: vhost_dev_init failed");
        goto err_virtio;
    }

    ret = vhost_vsock_set_guest_cid(vdev);                                 /* 设置guest_cid */
    if (ret < 0) {
        error_setg_errno(errp, -ret, "vhost-vsock: unable to set guest cid");
        goto err_vhost_dev;
    }
    return;
}
```

### vhost_vsock_common_realize

```c
void vhost_vsock_common_realize(VirtIODevice *vdev, const char *name)
{
    VHostVSockCommon *vvc = VHOST_VSOCK_COMMON(vdev);

    virtio_init(vdev, name, VIRTIO_ID_VSOCK,
                sizeof(struct virtio_vsock_config));

    /* Receive and transmit queues belong to vhost */
    vvc->recv_vq = virtio_add_queue(vdev, VHOST_VSOCK_QUEUE_SIZE,
                                      vhost_vsock_common_handle_output);
    vvc->trans_vq = virtio_add_queue(vdev, VHOST_VSOCK_QUEUE_SIZE,
                                       vhost_vsock_common_handle_output);

    /* The event queue belongs to QEMU */
    vvc->event_vq = virtio_add_queue(vdev, VHOST_VSOCK_QUEUE_SIZE,
                                       vhost_vsock_common_handle_output);

    vvc->vhost_dev.nvqs = ARRAY_SIZE(vvc->vhost_vqs);
    vvc->vhost_dev.vqs = vvc->vhost_vqs;

    vvc->post_load_timer = NULL;
}
```

### vhost_dev_init

vhost设置了一系列回调函数，这些函数会去调用ioctl，也就是会陷入到kernel去做相应的请求，这里有好几类ioctl;

- vhost_vring_ioctl
- vhost_dev_ioctl
- vhost_vsock_dev_ioctl

```c
int vhost_dev_init(struct vhost_dev *hdev, void *opaque,
                   VhostBackendType backend_type, uint32_t busyloop_timeout)
{
    uint64_t features;
    int i, r, n_initialized_vqs = 0;
    Error *local_err = NULL;

    hdev->vdev = NULL;
    hdev->migration_blocker = NULL;

    r = vhost_set_backend_type(hdev, backend_type);
    assert(r >= 0);

    r = hdev->vhost_ops->vhost_backend_init(hdev, opaque);     /* 会去调用实际的init函数 */
    if (r < 0) {
        goto fail;
    }

    r = hdev->vhost_ops->vhost_set_owner(hdev);
    if (r < 0) {
        VHOST_OPS_DEBUG("vhost_set_owner failed");
        goto fail;
    }

    r = hdev->vhost_ops->vhost_get_features(hdev, &features);
    if (r < 0) {
        VHOST_OPS_DEBUG("vhost_get_features failed");
        goto fail;
    }

    for (i = 0; i < hdev->nvqs; ++i, ++n_initialized_vqs) {        /* 初始化vq */
        r = vhost_virtqueue_init(hdev, hdev->vqs + i, hdev->vq_index + i);
        if (r < 0) {
            goto fail;
        }
    }

    if (busyloop_timeout) {
        for (i = 0; i < hdev->nvqs; ++i) {
            r = vhost_virtqueue_set_busyloop_timeout(hdev, hdev->vq_index + i,
                                                     busyloop_timeout);
            if (r < 0) {
                goto fail_busyloop;
            }
        }
    }

    hdev->features = features;

    hdev->memory_listener = (MemoryListener) {          /* 设置hdev的memory相关的回调函数 */
        .begin = vhost_begin,
        .commit = vhost_commit,
        .region_add = vhost_region_addnop,
        .region_nop = vhost_region_addnop,
        .log_start = vhost_log_start,
        .log_stop = vhost_log_stop,
        .log_sync = vhost_log_sync,
        .log_global_start = vhost_log_global_start,
        .log_global_stop = vhost_log_global_stop,
        .eventfd_add = vhost_eventfd_add,
        .eventfd_del = vhost_eventfd_del,
        .priority = 10
    };

    hdev->iommu_listener = (MemoryListener) {
        .region_add = vhost_iommu_region_add,
        .region_del = vhost_iommu_region_del,
    };

    if (hdev->migration_blocker == NULL) {
        if (!(hdev->features & (0x1ULL << VHOST_F_LOG_ALL))) {
            error_setg(&hdev->migration_blocker,
                       "Migration disabled: vhost lacks VHOST_F_LOG_ALL feature.");
        } else if (vhost_dev_log_is_shared(hdev) && !qemu_memfd_alloc_check()) {
            error_setg(&hdev->migration_blocker,
                       "Migration disabled: failed to allocate shared memory");
        }
    }

    if (hdev->migration_blocker != NULL) {
        r = migrate_add_blocker(hdev->migration_blocker, &local_err);
        if (local_err) {
            error_report_err(local_err);
            error_free(hdev->migration_blocker);
            goto fail_busyloop;
        }
    }

    hdev->mem = g_malloc0(offsetof(struct vhost_memory, regions));
    hdev->n_mem_sections = 0;
    hdev->mem_sections = NULL;
    hdev->log = NULL;
    hdev->log_size = 0;
    hdev->log_enabled = false;
    hdev->started = false;
    memory_listener_register(&hdev->memory_listener, &address_space_memory);
    QLIST_INSERT_HEAD(&vhost_devices, hdev, entry);

    if (used_memslots > hdev->vhost_ops->vhost_backend_memslots_limit(hdev)) {
        error_report("vhost backend memory slots limit is less"
                " than current number of present memory slots");
        r = -1;
        if (busyloop_timeout) {
            goto fail_busyloop;
        } else {
            goto fail;
        }
    }

    return 0;

fail_busyloop:
    while (--i >= 0) {
        vhost_virtqueue_set_busyloop_timeout(hdev, hdev->vq_index + i, 0);
    }
fail:
    hdev->nvqs = n_initialized_vqs;
    vhost_dev_cleanup(hdev);
    return r;
}
```



## Host侧驱动

### vhost_vsock_init

```c
static int __init vhost_vsock_init(void)
{
	int ret;

	ret = vsock_core_init(&vhost_transport.transport);            /* 初始化vhost_transport.transport */
	if (ret < 0)
		return ret;
	return misc_register(&vhost_vsock_misc);                      /* 注册vhost_vsock设备 */
};
```

### vsock_core_init

vsock_core_init  --> __vsock_core_init

```c
int __vsock_core_init(const struct vsock_transport *t, struct module *owner)
{
	int err = mutex_lock_interruptible(&vsock_register_mutex);

	if (err)
		return err;

	if (transport) {
		err = -EBUSY;
		goto err_busy;
	}

	/* Transport must be the owner of the protocol so that it can't
	 * unload while there are open sockets.
	 */
	vsock_proto.owner = owner;
	transport = t;

	vsock_device.minor = MISC_DYNAMIC_MINOR;
	err = misc_register(&vsock_device);
	if (err) {
		pr_err("Failed to register misc device\n");
		goto err_reset_transport;
	}

	err = proto_register(&vsock_proto, 1);	/* we want our slab */
	if (err) {
		pr_err("Cannot register vsock protocol\n");
		goto err_deregister_misc;
	}

	err = sock_register(&vsock_family_ops);
	if (err) {
		pr_err("could not register af_vsock (%d) address family: %d\n",
		       AF_VSOCK, err);
		goto err_unregister_proto;
	}

	mutex_unlock(&vsock_register_mutex);
	return 0;

err_unregister_proto:
	proto_unregister(&vsock_proto);
err_deregister_misc:
	misc_deregister(&vsock_device);
err_reset_transport:
	transport = NULL;
err_busy:
	mutex_unlock(&vsock_register_mutex);
	return err;
}
EXPORT_SYMBOL_GPL(__vsock_core_init);
```

### vhost_vsock_dev_open

```c
static int vhost_vsock_dev_open(struct inode *inode, struct file *file)
{
	struct vhost_virtqueue **vqs;
	struct vhost_vsock *vsock;
	int ret;

	/* This struct is large and allocation could fail, fall back to vmalloc
	 * if there is no other way.
	 */
	vsock = kvmalloc(sizeof(*vsock), GFP_KERNEL | __GFP_RETRY_MAYFAIL);
	if (!vsock)
		return -ENOMEM;

	vqs = kmalloc_array(ARRAY_SIZE(vsock->vqs), sizeof(*vqs), GFP_KERNEL);
	if (!vqs) {
		ret = -ENOMEM;
		goto out;
	}

	vsock->guest_cid = 0; /* no CID assigned yet */

	atomic_set(&vsock->queued_replies, 0);

	vqs[VSOCK_VQ_TX] = &vsock->vqs[VSOCK_VQ_TX];
	vqs[VSOCK_VQ_RX] = &vsock->vqs[VSOCK_VQ_RX];
	vsock->vqs[VSOCK_VQ_TX].handle_kick = vhost_vsock_handle_tx_kick;
	vsock->vqs[VSOCK_VQ_RX].handle_kick = vhost_vsock_handle_rx_kick;

	vhost_dev_init(&vsock->dev, vqs, ARRAY_SIZE(vsock->vqs), UIO_MAXIOV);

	file->private_data = vsock;
	spin_lock_init(&vsock->send_pkt_list_lock);
	INIT_LIST_HEAD(&vsock->send_pkt_list);
	vhost_work_init(&vsock->send_pkt_work, vhost_transport_send_pkt_work);
	return 0;

out:
	vhost_vsock_free(vsock);
	return ret;
}
```



## Guest侧驱动

### virtio_vsock_init

```c
static int __init virtio_vsock_init(void)
{
	int ret;

	virtio_vsock_workqueue = alloc_workqueue("virtio_vsock", 0, 0);
	if (!virtio_vsock_workqueue)
		return -ENOMEM;

	ret = register_virtio_driver(&virtio_vsock_driver);         /* 注册virtio_vsock_driver */
	if (ret)
		goto out_wq;

	ret = vsock_core_init(&virtio_transport.transport);         /* 初始化virtio_transport.transport   vsock_core_init和前面host端一样，此处不再分析*/
	if (ret)
		goto out_vdr;

	return 0;

out_vdr:
	unregister_virtio_driver(&virtio_vsock_driver);
out_wq:
	destroy_workqueue(virtio_vsock_workqueue);
	return ret;
}
```

### virtio_vsock_probe

```c
static int virtio_vsock_probe(struct virtio_device *vdev)
{
	vq_callback_t *callbacks[] = {                  /* vq的回调函数 */
		virtio_vsock_rx_done,
		virtio_vsock_tx_done,
		virtio_vsock_event_done,
	};
	static const char * const names[] = {
		"rx",
		"tx",
		"event",
	};
	struct virtio_vsock *vsock = NULL;
	int ret;

	ret = mutex_lock_interruptible(&the_virtio_vsock_mutex);
	if (ret)
		return ret;

	/* Only one virtio-vsock device per guest is supported */
	if (the_virtio_vsock) {
		ret = -EBUSY;
		goto out;
	}

	vsock = kzalloc(sizeof(*vsock), GFP_KERNEL);   /* 创建virtio_vsock */
	if (!vsock) {
		ret = -ENOMEM;
		goto out;
	}

	vsock->vdev = vdev;                            /* 设置virtio_device */

	ret = virtio_find_vqs(vsock->vdev, VSOCK_VQ_MAX,     /* 生成vq的实体 */
			      vsock->vqs, callbacks, names,
			      NULL);
	if (ret < 0)
		goto out;

	virtio_vsock_update_guest_cid(vsock);         /* 更新guest_cid的值 */

	vsock->rx_buf_nr = 0;
	vsock->rx_buf_max_nr = 0;
	atomic_set(&vsock->queued_replies, 0);

	vdev->priv = vsock;
	the_virtio_vsock = vsock;                     /* 把virtio_vsock赋值给全局变量the_virtio_vsock */
	mutex_init(&vsock->tx_lock);
	mutex_init(&vsock->rx_lock);
	mutex_init(&vsock->event_lock);
	spin_lock_init(&vsock->send_pkt_list_lock);
	INIT_LIST_HEAD(&vsock->send_pkt_list);
	spin_lock_init(&vsock->loopback_list_lock);
	INIT_LIST_HEAD(&vsock->loopback_list);
	INIT_WORK(&vsock->rx_work, virtio_transport_rx_work);
	INIT_WORK(&vsock->tx_work, virtio_transport_tx_work);
	INIT_WORK(&vsock->event_work, virtio_transport_event_work);
	INIT_WORK(&vsock->send_pkt_work, virtio_transport_send_pkt_work);
	INIT_WORK(&vsock->loopback_work, virtio_transport_loopback_work);

	mutex_lock(&vsock->rx_lock);
	virtio_vsock_rx_fill(vsock);               /* fill recv  */
	mutex_unlock(&vsock->rx_lock);

	mutex_lock(&vsock->event_lock);
	virtio_vsock_event_fill(vsock);            /* fill event */
	mutex_unlock(&vsock->event_lock);

	mutex_unlock(&the_virtio_vsock_mutex);
	return 0;

out:
	kfree(vsock);
	mutex_unlock(&the_virtio_vsock_mutex);
	return ret;
}
```

