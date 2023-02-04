# recv

### recv函数

```c
int s = socket(AF_VSOCK, SOCK_STREAM, 0);
struct sockaddr_vm addr;
memset(&addr, 0, sizeof(struct sockaddr_vm));
addr.svm_family = AF_VSOCK;
addr.svm_port = 9999;
addr.svm_cid = VMADDR_CID_HOST;
connect(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));

send(s, data, prefix_size, 0);

char buf[2];
recv(s, &buf, 2, 0);
```



## sys_recvfrom函数

别的废话就不讲了，和前面bind类似。

```c
COMPAT_SYSCALL_DEFINE6(recvfrom, int, fd, void __user *, buf, compat_size_t, len,
		       unsigned int, flags, struct sockaddr __user *, addr,
		       int __user *, addrlen)
{
	return __compat_sys_recvfrom(fd, buf, len, flags, addr, addrlen);
}

static inline long __compat_sys_recvfrom(int fd, void __user *buf,
					 compat_size_t len, unsigned int flags,
					 struct sockaddr __user *addr,
					 int __user *addrlen)
{
	return __sys_recvfrom(fd, buf, len, flags | MSG_CMSG_COMPAT, addr,
			      addrlen);
}

/*
 *	Receive a frame from the socket and optionally record the address of the
 *	sender. We verify the buffers are writable and if needed move the
 *	sender address from kernel to user space.
 */
__sys_recvfrom
    sock_recvmsg
```



## sock_recvmsg函数

```c
/**
 *	sock_recvmsg - receive a message from @sock
 *	@sock: socket
 *	@msg: message to receive
 *	@flags: message flags
 *
 *	Receives @msg from @sock, passing through LSM. Returns the total number
 *	of bytes received, or an error.
 */

static inline int sock_recvmsg_nosec(struct socket *sock, struct msghdr *msg,
				     int flags)
{
	return sock->ops->recvmsg(sock, msg, msg_data_left(msg), flags);   /* 调用实际的recv函数 */
}

int sock_recvmsg(struct socket *sock, struct msghdr *msg, int flags)
{
	int err = security_socket_recvmsg(sock, msg, msg_data_left(msg), flags);

	return err ?: sock_recvmsg_nosec(sock, msg, flags);
}
EXPORT_SYMBOL(sock_recvmsg);
```



## vsock_stream_recvmsg

```c
vsock_stream_recvmsg
    transport->stream_dequeue
    	virtio_transport_stream_dequeue
    		virtio_transport_stream_do_dequeue
```
