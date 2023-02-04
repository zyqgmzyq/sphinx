# send

### send函数

```c
int s = socket(AF_VSOCK, SOCK_STREAM, 0);
struct sockaddr_vm addr;
memset(&addr, 0, sizeof(struct sockaddr_vm));
addr.svm_family = AF_VSOCK;
addr.svm_port = 9999;
addr.svm_cid = VMADDR_CID_HOST;
connect(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));

send(s, data, prefix_size, 0);
```



## sys_sendto函数

别的废话就不讲了，和前面bind类似。

```c
SYSCALL_DEFINE6(sendto, int, fd, void __user *, buff, size_t, len,
		unsigned int, flags, struct sockaddr __user *, addr,
		int, addr_len)
{
	return __sys_sendto(fd, buff, len, flags, addr, addr_len);
}

/*
 *	Send a datagram to a given address. We move the address into kernel
 *	space and check the user space data area is readable before invoking
 *	the protocol.
 */
int __sys_sendto(int fd, void __user *buff, size_t len, unsigned int flags,
		 struct sockaddr __user *addr,  int addr_len)
{
	struct socket *sock;
	struct sockaddr_storage address;
	int err;
	struct msghdr msg;
	struct iovec iov;
	int fput_needed;

	err = import_single_range(WRITE, buff, len, &iov, &msg.msg_iter);
	if (unlikely(err))
		return err;
	sock = sockfd_lookup_light(fd, &err, &fput_needed);   /* 根据fd拿到对应的socket */
	if (!sock)
		goto out;

	msg.msg_name = NULL;
	msg.msg_control = NULL;
	msg.msg_controllen = 0;
	msg.msg_namelen = 0;
	if (addr) {
		err = move_addr_to_kernel(addr, addr_len, &address);
		if (err < 0)
			goto out_put;
		msg.msg_name = (struct sockaddr *)&address;
		msg.msg_namelen = addr_len;
	}
	if (sock->file->f_flags & O_NONBLOCK)
		flags |= MSG_DONTWAIT;
	msg.msg_flags = flags;
	err = sock_sendmsg(sock, &msg);                /* 发送数据 */

out_put:
	fput_light(sock->file, fput_needed);
out:
	return err;
}
```



## sock_sendmsg函数

```c
/**
 *	sock_sendmsg - send a message through @sock
 *	@sock: socket
 *	@msg: message to send
 *
 *	Sends @msg through @sock, passing through LSM.
 *	Returns the number of bytes sent, or an error code.
 */

static inline int sock_sendmsg_nosec(struct socket *sock, struct msghdr *msg)
{
	int ret = sock->ops->sendmsg(sock, msg, msg_data_left(msg));   /* 调用实际的send函数 */
	BUG_ON(ret == -EIOCBQUEUED);
	return ret;
}

int sock_sendmsg(struct socket *sock, struct msghdr *msg)
{
	int err = security_socket_sendmsg(sock, msg,
					  msg_data_left(msg));

	return err ?: sock_sendmsg_nosec(sock, msg);
}
EXPORT_SYMBOL(sock_sendmsg);
```



## vsock_stream_sendmsg

```c
static int vsock_stream_sendmsg(struct socket *sock, struct msghdr *msg,
				size_t len)
{
	struct sock *sk = sock->sk;

	/* Wait for room in the produce queue to enqueue our user's data. */
	timeout = sock_sndtimeo(sk, msg->msg_flags & MSG_DONTWAIT);

	err = transport->notify_send_init(vsk, &send_data);        /* 我要开始发数据拉 */
	if (err < 0)
		goto out;

	while (total_written < len) {                              /* 循环发送 直到发送完所有的 */
		ssize_t written;

		add_wait_queue(sk_sleep(sk), &wait); 
		while (vsock_stream_has_space(vsk) == 0 &&              /* 如果steam没有空间了 */
		       sk->sk_err == 0 &&
		       !(sk->sk_shutdown & SEND_SHUTDOWN) &&
		       !(vsk->peer_shutdown & RCV_SHUTDOWN)) {

			err = transport->notify_send_pre_block(vsk, &send_data);      /* 通知发送前一个block */
			if (err < 0) {
				remove_wait_queue(sk_sleep(sk), &wait);
				goto out_err;
			}

			release_sock(sk);
			timeout = wait_woken(&wait, TASK_INTERRUPTIBLE, timeout);
			lock_sock(sk);
			if (signal_pending(current)) {
				err = sock_intr_errno(timeout);
				remove_wait_queue(sk_sleep(sk), &wait);
				goto out_err;
			} else if (timeout == 0) {
				err = -EAGAIN;
				remove_wait_queue(sk_sleep(sk), &wait);
				goto out_err;
			}
		}
		remove_wait_queue(sk_sleep(sk), &wait);

		/* These checks occur both as part of and after the loop
		 * conditional since we need to check before and after
		 * sleeping.
		 */
		if (sk->sk_err) {
			err = -sk->sk_err;
			goto out_err;
		} else if ((sk->sk_shutdown & SEND_SHUTDOWN) ||
			   (vsk->peer_shutdown & RCV_SHUTDOWN)) {
			err = -EPIPE;
			goto out_err;
		}

		err = transport->notify_send_pre_enqueue(vsk, &send_data);
		if (err < 0)
			goto out_err;

		/* Note that enqueue will only write as many bytes as are free
		 * in the produce queue, so we don't need to ensure len is
		 * smaller than the queue size.  It is the caller's
		 * responsibility to check how many bytes we were able to send.
		 */

		written = transport->stream_enqueue(               /* 发送数据流 */
				vsk, msg,
				len - total_written);
		if (written < 0) {
			err = -ENOMEM;
			goto out_err;
		}

		total_written += written;

		err = transport->notify_send_post_enqueue(
				vsk, written, &send_data);
		if (err < 0)
			goto out_err;

	}
	......
}
```



## virtio_transport_stream_enqueue函数

```c
ssize_t
virtio_transport_stream_enqueue(struct vsock_sock *vsk,
				struct msghdr *msg,
				size_t len)
{
	struct virtio_vsock_pkt_info info = {
		.op = VIRTIO_VSOCK_OP_RW,
		.type = VIRTIO_VSOCK_TYPE_STREAM,
		.msg = msg,
		.pkt_len = len,
		.vsk = vsk,
	};

	return virtio_transport_send_pkt_info(vsk, &info);
}
EXPORT_SYMBOL_GPL(virtio_transport_stream_enqueue);
```

然后就是调用virtio_transport_send_pkt_info 函数，后面都是和connect时候一样了，区别在于传入的info参数不同；

virtio_transport_send_pkt_info --> virtio_transport_get_ops()->send_pkt(pkt) --> virtio_transport_send_pkt --> virtio_transport_send_pkt_work；



然后就跳转到virtio_vsock_rx_done函数，virtio_vsock_rx_done -->  virtio_transport_rx_work  --> virtio_transport_recv_pkt --> virtio_transport_recv_connected

```c
static int
virtio_transport_recv_connected(struct sock *sk,
				struct virtio_vsock_pkt *pkt)
{
	struct vsock_sock *vsk = vsock_sk(sk);
	struct virtio_vsock_sock *vvs = vsk->trans;
	int err = 0;

	switch (le16_to_cpu(pkt->hdr.op)) {
	case VIRTIO_VSOCK_OP_RW:
		pkt->len = le32_to_cpu(pkt->hdr.len);
		pkt->off = 0;

		spin_lock_bh(&vvs->rx_lock);
		virtio_transport_inc_rx_pkt(vvs, pkt);
		list_add_tail(&pkt->list, &vvs->rx_queue);
		spin_unlock_bh(&vvs->rx_lock);

		sk->sk_data_ready(sk);
		return err;
	case VIRTIO_VSOCK_OP_CREDIT_UPDATE:
		sk->sk_write_space(sk);
		break;
	case VIRTIO_VSOCK_OP_SHUTDOWN:
		if (le32_to_cpu(pkt->hdr.flags) & VIRTIO_VSOCK_SHUTDOWN_RCV)
			vsk->peer_shutdown |= RCV_SHUTDOWN;
		if (le32_to_cpu(pkt->hdr.flags) & VIRTIO_VSOCK_SHUTDOWN_SEND)
			vsk->peer_shutdown |= SEND_SHUTDOWN;
		if (vsk->peer_shutdown == SHUTDOWN_MASK &&
		    vsock_stream_has_data(vsk) <= 0)
			sk->sk_state = TCP_CLOSING;
		if (le32_to_cpu(pkt->hdr.flags))
			sk->sk_state_change(sk);
		break;
	case VIRTIO_VSOCK_OP_RST:
		virtio_transport_do_close(vsk, true);
		break;
	default:
		err = -EINVAL;
		break;
	}

	virtio_transport_free_pkt(pkt);
	return err;
}
```

