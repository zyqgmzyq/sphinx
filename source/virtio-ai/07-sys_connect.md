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
		memcpy(&vsk->remote_addr, remote_addr,
		       sizeof(vsk->remote_addr));

		err = vsock_auto_bind(vsk);          /* 自动bind这个socket到local_addr */
		if (err)
			goto out;
 
		sk->sk_state = TCP_SYN_SENT;         /* 设置sk->sk_state为TCP_SYN_SENT */

		err = transport->connect(vsk);       /* 执行实际的connect函数 */
		if (err < 0)
			goto out;

		/* Mark sock as connecting and set the error code to in
		 * progress in case this is a non-blocking connect.
		 */
		sock->state = SS_CONNECTING;         /* 设置sock->state为SS_CONNECTING */
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
		.op = VIRTIO_VSOCK_OP_REQUEST,
		.type = VIRTIO_VSOCK_TYPE_STREAM,
		.vsk = vsk,
	};

	return virtio_transport_send_pkt_info(vsk, &info);
}
EXPORT_SYMBOL_GPL(virtio_transport_connect);
```

### virtio_transport_send_pkt_work

virtio_transport_send_pkt_info --> virtio_transport_get_ops()->send_pkt(pkt) --> virtio_transport_send_pkt --> virtio_transport_send_pkt_work

virtio_transport_send_pkt_work函数把pktde hdr和buf添加到sgs，使用vq发送到qemu侧；

qemu侧接收完之后会触发中断函数virtio_vsock_tx_done；



**? 这里不知道是怎么跳转到这里的**

virtio_vsock_rx_done -->  virtio_transport_rx_work  --> virtio_transport_recv_pkt

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

