# connect

## connect函数

```c
int s = socket(AF_VSOCK, SOCK_STREAM, 0);
struct sockaddr_vm addr;
memset(&addr, 0, sizeof(struct sockaddr_vm));
addr.svm_family = AF_VSOCK;
addr.svm_port = 9999;
addr.svm_cid = VMADDR_CID_HOST;
connect(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));
```

## sys_connect函数

```c
SYSCALL_DEFINE3(connect, int, fd, struct sockaddr __user *, uservaddr,
		int, addrlen)
{
	return __sys_connect(fd, uservaddr, addrlen);
}

/*
 *	Attempt to connect to a socket with the server address.  The address
 *	is in user space so we verify it is OK and move it to kernel space.
 *
 *	For 1003.1g we need to add clean support for a bind to AF_UNSPEC to
 *	break bindings
 *
 *	NOTE: 1003.1g draft 6.3 is broken with respect to AX.25/NetROM and
 *	other SEQPACKET protocols that take time to connect() as it doesn't
 *	include the -EINPROGRESS status for such sockets.
 */

int __sys_connect(int fd, struct sockaddr __user *uservaddr, int addrlen)
{
	struct socket *sock;
	struct sockaddr_storage address;
	int err, fput_needed;

	sock = sockfd_lookup_light(fd, &err, &fput_needed);            /* 根据fd找到对应的socket对象 */
	if (!sock)
		goto out;
	err = move_addr_to_kernel(uservaddr, addrlen, &address);       /* 将用户态的地址拷贝到内核中 */
	if (err < 0)
		goto out_put;

	err = security_socket_connect(sock, (struct sockaddr *)&address, addrlen);
	if (err)
		goto out_put;

	err = sock->ops->connect(sock, (struct sockaddr *)&address, addrlen,  /* 调用实际的connect函数 */
				 sock->file->f_flags);
out_put:
	fput_light(sock->file, fput_needed);
out:
	return err;
}
```



## vsock_stream_connect

```c
static int vsock_stream_connect(struct socket *sock, struct sockaddr *addr,
				int addr_len, int flags)
{
	int err;
	struct sock *sk;
	struct vsock_sock *vsk;
	struct sockaddr_vm *remote_addr;
	long timeout;
	DEFINE_WAIT(wait);

	err = 0;
	sk = sock->sk;
	vsk = vsock_sk(sk);

	lock_sock(sk);

	/* XXX AF_UNSPEC should make us disconnect like AF_INET. */
	switch (sock->state) {
	case SS_CONNECTED:
		err = -EISCONN;
		goto out;
	case SS_DISCONNECTING:
		err = -EINVAL;
		goto out;
	case SS_CONNECTING:
		/* This continues on so we can move sock into the SS_CONNECTED
		 * state once the connection has completed (at which point err
		 * will be set to zero also).  Otherwise, we will either wait
		 * for the connection or return -EALREADY should this be a
		 * non-blocking call.
		 */
		err = -EALREADY;
		break;
	default:
		if ((sk->sk_state == TCP_LISTEN) ||
		    vsock_addr_cast(addr, addr_len, &remote_addr) != 0) {
			err = -EINVAL;
			goto out;
		}

		/* The hypervisor and well-known contexts do not have socket
		 * endpoints.
		 */
		if (!transport->stream_allow(remote_addr->svm_cid,
					     remote_addr->svm_port)) {
			err = -ENETUNREACH;
			goto out;
		}

		/* Set the remote address that we are connecting to. */
		memcpy(&vsk->remote_addr, remote_addr,     /* 把addr复制到remote_addr */
		       sizeof(vsk->remote_addr));

		err = vsock_auto_bind(vsk);                /* 自动bind这个socket到local_addr */
		if (err)
			goto out;
 
		sk->sk_state = TCP_SYN_SENT;                /* 设置sk->sk_state为TCP_SYN_SENT */

		err = transport->connect(vsk);              /* 执行实际的connect函数 */
		if (err < 0)
			goto out;

		/* Mark sock as connecting and set the error code to in
		 * progress in case this is a non-blocking connect.
		 */
		sock->state = SS_CONNECTING;                /* 设置sock->state为SS_CONNECTING */
		err = -EINPROGRESS;
	}

	/* The receive path will handle all communication until we are able to
	 * enter the connected state.  Here we wait for the connection to be
	 * completed or a notification of an error.
	 */
	timeout = vsk->connect_timeout;
	prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);

	while (sk->sk_state != TCP_ESTABLISHED && sk->sk_err == 0) {     /* 循环等待sk->sk_state状态变为TCP_ESTABLISHED */
		if (flags & O_NONBLOCK) {
			/* If we're not going to block, we schedule a timeout
			 * function to generate a timeout on the connection
			 * attempt, in case the peer doesn't respond in a
			 * timely manner. We hold on to the socket until the
			 * timeout fires.
			 */
			sock_hold(sk);
			schedule_delayed_work(&vsk->connect_work, timeout);

			/* Skip ahead to preserve error code set above. */
			goto out_wait;
		}

		release_sock(sk);
		timeout = schedule_timeout(timeout);
		lock_sock(sk);

		if (signal_pending(current)) {
			err = sock_intr_errno(timeout);
			sk->sk_state = TCP_CLOSE;
			sock->state = SS_UNCONNECTED;
			vsock_transport_cancel_pkt(vsk);
			goto out_wait;
		} else if (timeout == 0) {
			err = -ETIMEDOUT;
			sk->sk_state = TCP_CLOSE;
			sock->state = SS_UNCONNECTED;
			vsock_transport_cancel_pkt(vsk);
			goto out_wait;
		}

		prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);
	}

	if (sk->sk_err) {
		err = -sk->sk_err;
		sk->sk_state = TCP_CLOSE;
		sock->state = SS_UNCONNECTED;
	} else {
		err = 0;
	}

out_wait:
	finish_wait(sk_sleep(sk), &wait);
out:
	release_sock(sk);
	return err;
}
```

## virtio_transport_connect函数

```c
int virtio_transport_connect(struct vsock_sock *vsk)
{
	struct virtio_vsock_pkt_info info = {
		.op = VIRTIO_VSOCK_OP_REQUEST,     /* request op */
		.type = VIRTIO_VSOCK_TYPE_STREAM,
		.vsk = vsk,
	};

	return virtio_transport_send_pkt_info(vsk, &info);
}
EXPORT_SYMBOL_GPL(virtio_transport_connect);
```



## virtio_transport_send_pkt_info

```c
static int virtio_transport_send_pkt_info(struct vsock_sock *vsk,
					  struct virtio_vsock_pkt_info *info)
{
	u32 src_cid, src_port, dst_cid, dst_port;
	struct virtio_vsock_sock *vvs;
	struct virtio_vsock_pkt *pkt;
	u32 pkt_len = info->pkt_len;

	src_cid = vm_sockets_get_local_cid();         /* 获取local_cid   这里应该是guest_cid */ 
	src_port = vsk->local_addr.svm_port;
	if (!info->remote_cid) {
		dst_cid	= vsk->remote_addr.svm_cid;       /* 从用户态传来的addr复制来的 */
		dst_port = vsk->remote_addr.svm_port;
	} else {
		dst_cid = info->remote_cid;
		dst_port = info->remote_port;
	}

	vvs = vsk->trans;

	/* we can send less than pkt_len bytes */
	if (pkt_len > VIRTIO_VSOCK_DEFAULT_RX_BUF_SIZE)
		pkt_len = VIRTIO_VSOCK_DEFAULT_RX_BUF_SIZE;

	/* virtio_transport_get_credit might return less than pkt_len credit */
	pkt_len = virtio_transport_get_credit(vvs, pkt_len);    

	/* Do not send zero length OP_RW pkt */
	if (pkt_len == 0 && info->op == VIRTIO_VSOCK_OP_RW)
		return pkt_len;

	pkt = virtio_transport_alloc_pkt(info, pkt_len,           /* 创建pkt info */
					 src_cid, src_port,
					 dst_cid, dst_port);
	if (!pkt) {
		virtio_transport_put_credit(vvs, pkt_len);
		return -ENOMEM;
	}

	virtio_transport_inc_tx_pkt(vvs, pkt);

	return virtio_transport_get_ops()->send_pkt(pkt);
}
```



## virtio_transport_send_pkt_work

virtio_transport_send_pkt_info --> virtio_transport_get_ops()->send_pkt(pkt) --> virtio_transport_send_pkt --> virtio_transport_send_pkt_work;

- virtio_transport_send_pkt_work函数把pktde hdr和buf添加到sgs，使用vq发送到qemu侧；然后调用virtqueue_kick函数通知qemu侧；qemu处理notify函数具体见**附录1**；

- guest产生kick后， host内核会调用函数vhost_vsock_handle_tx_kick（为啥会调用到这见**附录2**）；该函数接收guest传来的pkt包并进行相对应的处理，处理完之后会使用eventfd通知guest(具体见**附录3**);

    host侧会调用virtio_transport_recv_listen函数，该函数会新建一个sock(child)，并把该sock添加到全局的connect table，然后调用virtio_transport_send_response-->vhost_transport_send_pkt-->vhost_transport_send_pkt_work-->vhost_transport_do_send_pkt函数，发送一个response pkt给guest;  

    **Note:**host发送给guest是使用\>vqs[VSOCK_VQ_RX]；而guest发送给host是使用**vqs[VSOCK_VQ_TX]**;因此会触发guest侧的virtio_vsock_rx_done 函数

- host侧接收完之后通知guest会触发guest侧的中断函数virtio_vsock_tx_done-->virtio_transport_tx_work；无非就是回收buffer或者接收vhost转给它的报文;

- guest侧跳转到virtio_vsock_rx_done -->  virtio_transport_rx_work  --> virtio_transport_recv_pkt

然后virtio_transport_recv_pkt函数里面做了以下工作：

- 根据recv得到的pkt获取到对应的sk和vsk
- 根据sk->state来做相应的处理，

```c
switch (sk->sk_state) { 
	case TCP_LISTEN:
		virtio_transport_recv_listen(sk, pkt);
		virtio_transport_free_pkt(pkt);
		break;
	case TCP_SYN_SENT:
		virtio_transport_recv_connecting(sk, pkt);
		virtio_transport_free_pkt(pkt);
		break;
	case TCP_ESTABLISHED:
		virtio_transport_recv_connected(sk, pkt);
		break;
	case TCP_CLOSING:
		virtio_transport_recv_disconnecting(sk, pkt);
		virtio_transport_free_pkt(pkt);
		break;
	default:
		virtio_transport_free_pkt(pkt);
		break;
	}
```

前面vsock_stream_connect函数里面设置的sk->state是TCP_SYN_SENT，所以此处会去调用virtio_transport_recv_connecting函数



## virtio_transport_recv_connecting

```c
static int
virtio_transport_recv_connecting(struct sock *sk,
				 struct virtio_vsock_pkt *pkt)
{
	struct vsock_sock *vsk = vsock_sk(sk);
	int err;
	int skerr;

	switch (le16_to_cpu(pkt->hdr.op)) {
	case VIRTIO_VSOCK_OP_RESPONSE:
		sk->sk_state = TCP_ESTABLISHED;                /* 设置sk->sk_state为TCP_ESTABLISHED */
		sk->sk_socket->state = SS_CONNECTED;           /* 设置sk->sk_socket->state为SS_CONNECTED */
		vsock_insert_connected(vsk);                   /* 把vsk插入到connected_table */
		sk->sk_state_change(sk);           
		break;
	case VIRTIO_VSOCK_OP_INVALID:
		break;
	case VIRTIO_VSOCK_OP_RST:
		skerr = ECONNRESET;
		err = 0;
		goto destroy;
	default:
		skerr = EPROTO;
		err = -EINVAL;
		goto destroy;
	}
	return 0;

destroy:
	virtio_transport_reset(vsk, pkt);
	sk->sk_state = TCP_CLOSE;
	sk->sk_err = skerr;
	sk->sk_error_report(sk);
	return err;
}
```



## 附录1：kick (guest通知host)

qemu侧处理guest的通知，一般**称guest侧通知host侧的行为为kick**

```c
void virtio_queue_notify(VirtIODevice *vdev, int n)
{
    VirtQueue *vq = &vdev->vq[n];

    if (unlikely(!vq->vring.desc || vdev->broken)) {
        return;
    }

    trace_virtio_queue_notify(vdev, vq - vdev->vq, vq);
    if (vq->host_notifier_enabled) {  
        event_notifier_set(&vq->host_notifier);   /* vhost模式，会去写eventfd */
    } else if (vq->handle_output) {
        vq->handle_output(vdev, vq);       /* 非vhost模式，跳转到对应的handle_output函数（qemu实现）  比如virtio-net里的virtio_net_handle_ctrl */

        if (unlikely(vdev->start_on_kick)) {
            virtio_set_started(vdev, true);
        }
    }
}
```

guest 在 kick host 时采用 eventfd 通知**内核线程 `vhost_worker`**，qemu侧会调用到**virtio_queue_host_notifier_read**函数，**此函数实际就是调用handle_output去处理IO请求，如果是vhost模式则唤醒vhost work，否则唤醒qemu。**

也就是说guest调用kick，如果该eventfd是由qemu侧来监听的，则会执行对应的qemu函数`kvm_handle_io()`；**如果是vhost来监听的，则直接在vhost内核模块执行vhost->handle_kick()**。



## 附录2：vhost-guest通信

【vhost】：https://blog.csdn.net/zgy666/article/details/89635669

**kernnel vhost方式通过**vhost_vring_ioctl 设置**VHOST_SET_VRING_CALL，设置irqfd，把中断注入guest；通过** **VHOST_SET_VRING_KICK，设置ioeventfd， 获取guest notify**

### qemu侧vhost_vsock_device_realize

```c
vhost_vsock_device_realize
    /* open vhost-vsock 这是host的driver */
    vhostfd = open("/dev/vhost-vsock", O_RDWR);
	
	/* 把vhost_dev绑定到vvc结构体(VHostVSockCommon) */
	vhost_vsock_common_realize
    	vvc->vhost_dev.nvqs = ARRAY_SIZE(vvc->vhost_vqs);
    	vvc->vhost_dev.vqs = vvc->vhost_vqs;

	/* 初始化vhost_dev相关的一系列回调函数 */
	vhost_dev_init(&vvc->vhost_dev, (void *)(uintptr_t)vhostfd,
                         VHOST_BACKEND_TYPE_KERNEL, 0);
		vhost_virtqueue_init
            dev->vhost_ops->vhost_set_vring_call(dev, &file); 
				vhost_kernel_set_vring_call
					vhost_kernel_call(dev, VHOST_SET_VRING_CALL, file);     /* 这里会调用到ioctl 可以后面一起看 */
```

### 然后启动linux,linux在加载vhost-vsock时候，qemu侧会调用到vhost_vsock_set_status

![image-20210727193520437](07-sys_connect.assets/image-20210727193520437.png)

```c
vhost_vsock_set_status
	vhost_vsock_common_start
    	vhost_dev_start(&vvc->vhost_dev, vdev);
			vhost_virtqueue_start
                dev->vhost_ops->vhost_set_vring_kick(dev, &file);
					vhost_kernel_set_vring_kick(dev, &file);
                        vhost_kernel_call(dev, VHOST_SET_VRING_KICK, file);
```

vhost_kernel_call函数是调用一个ioctl陷入到内核态

```c
static int vhost_kernel_call(struct vhost_dev *dev, unsigned long int request,
                             void *arg)
{
    int fd = (uintptr_t) dev->opaque;

    assert(dev->vhost_ops->backend_type == VHOST_BACKEND_TYPE_KERNEL);

    return ioctl(fd, request, arg);
}
```

### 内核态vhost_vsock_dev_ioctl

```c
vhost_vsock_dev_ioctl
	vhost_vring_ioctl
        case VHOST_SET_VRING_KICK:           /*  获取guest notify  */
            if (copy_from_user(&f, argp, sizeof f)) {
                r = -EFAULT;
                break;
            }
            eventfp = f.fd == -1 ? NULL : eventfd_fget(f.fd);
            if (IS_ERR(eventfp)) {
                r = PTR_ERR(eventfp);
                break;
            }
            if (eventfp != vq->kick) {
                pollstop = (filep = vq->kick) != NULL;
                pollstart = (vq->kick = eventfp) != NULL;
            } else
                filep = eventfp;
            break;
		case VHOST_SET_VRING_CALL:         /*  把中断注入guest  */
            if (copy_from_user(&f, argp, sizeof f)) {
                r = -EFAULT;
                break;
            }
            ctx = f.fd == -1 ? NULL : eventfd_ctx_fdget(f.fd);
            if (IS_ERR(ctx)) {
                r = PTR_ERR(ctx);
                break;
            }
            swap(ctx, vq->call_ctx);
            break;

		if (!IS_ERR_OR_NULL(ctx))
			eventfd_ctx_put(ctx);        /* VHOST_SET_VRING_CALL: 设置irqfd，把中断注入guest */
        if (filep)                       /* VHOST_SET_VRING_KICK: 设置ioeventfd， 获取guest notify */
            fput(filep);
        if (pollstart && vq->handle_kick) 
            r = vhost_poll_start(&vq->poll, vq->kick);    /* vhost_pool start */
					vhost_poll_wakeup
                    	vhost_work_queue                   /* vhost后台线程vhost_worker */
```

再来看这个vq->handle_kick是在vhost_vsock_dev_open函数里面设置的

```c
vhost_vsock_dev_open
	vqs[VSOCK_VQ_TX] = &vsock->vqs[VSOCK_VQ_TX];
	vqs[VSOCK_VQ_RX] = &vsock->vqs[VSOCK_VQ_RX];
	/* 设置vq的handle_kick回调函数 */
	vsock->vqs[VSOCK_VQ_TX].handle_kick = vhost_vsock_handle_tx_kick;
	vsock->vqs[VSOCK_VQ_RX].handle_kick = vhost_vsock_handle_rx_kick;

	/*  初始化vhost_vsock的vhost_poll */
	vhost_dev_init
        if (vq->handle_kick)
            vhost_poll_init(&vq->poll, vq->handle_kick,EPOLLIN, dev);
```

每个vhost_net_virtqueue都有自己的vhost_poll，该poll是监控数据的核心机制，而现阶段仅仅是初始化。

```c
void vhost_poll_init(struct vhost_poll *poll, vhost_work_fn_t fn,
             unsigned long mask, struct vhost_dev *dev)
{
    init_waitqueue_func_entry(&poll->wait, vhost_poll_wakeup);
    init_poll_funcptr(&poll->table, vhost_poll_func);
    poll->mask = mask;
    poll->dev = dev;
    poll->wqh = NULL;
    /*设置处理函数*/
    vhost_work_init(&poll->work, fn);
}
```

vhost_poll_wakeup是自定义的等待队列唤醒函数，在对某个描述符poll的时候会把vhost_poll加入到对应描述符的等待队列中，而该函数就是描述符有信号时的唤醒函数，唤醒函数中会验证当前信号是否满足vhost_poll对应的请求掩码，如果满足调用vhost_poll_queue->vhost_work_queue,该函数如下

```c
void vhost_work_queue(struct vhost_dev *dev, struct vhost_work *work)
{
	if (!dev->worker)
		return;

	if (!test_and_set_bit(VHOST_WORK_QUEUED, &work->flags)) {
		/* 把vhost_work加入到设备的工作链表，该链表会在后台线程中遍历处理 */
		llist_add(&work->node, &dev->work_list);
        /* 唤醒工作线程 */    
		wake_up_process(dev->worker);
	}
}
```

该函数会把vhost_work加入到设备的工作队列，然后唤醒vhost后台线程vhost_worker，vhost_worker会遍历设备的工作队列，调用work->fn即之前我们注册的处理函数vhost_vsock_handle_tx_kick和vhost_vsock_handle_rx_kick，这样数据包就得到了处理。

## 附录3：host通知guest

前面说到guest产生kick后，host侧会跳转到vhost_vsock_handle_tx_kick；

``` c
vhost_vsock_handle_tx_kick
    vhost_vsock_alloc_pkt      /* 创建pkt,pkt的具体信息（pkt->buf,pkt->hdr等）是从vq里取出来的 */
    virtio_transport_recv_pkt  /* virtio_transport对pkt进行相应处理 */
    vhost_add_used             /* 将已经使用的buffer信息回填给Guest */
    vhost_signal               /* 调用vhost_signal通知Guest接收报文 */
    	vhost_notify
    	eventfd_signal
```

## 遗留：

eventfd详细的运作方式
