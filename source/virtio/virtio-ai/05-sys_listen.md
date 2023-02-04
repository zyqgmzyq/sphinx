# listen

### listen函数

```c
int s = socket(AF_VSOCK, SOCK_STREAM, 0);
memset(&addr, 0, sizeof(struct sockaddr_vm));
addr.svm_family = AF_VSOCK;
addr.svm_port = 9999;
addr.svm_cid = VMADDR_CID_HOST;

bind(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));

listen(s, 0);
```



## sys_listen函数

别的废话就不讲了，和前面bind类似。

```c
SYSCALL_DEFINE2(listen, int, fd, int, backlog)
{
	return __sys_listen(fd, backlog);
}

/*
 *	Perform a listen. Basically, we allow the protocol to do anything
 *	necessary for a listen, and if that works, we mark the socket as
 *	ready for listening.
 */

int __sys_listen(int fd, int backlog)
{
	struct socket *sock;
	int err, fput_needed;
	int somaxconn;

	sock = sockfd_lookup_light(fd, &err, &fput_needed);               /* 根据fd找到对应的sock */
	if (sock) {
		somaxconn = sock_net(sock->sk)->core.sysctl_somaxconn;
		if ((unsigned int)backlog > somaxconn)
			backlog = somaxconn;

		err = security_socket_listen(sock, backlog);
		if (!err)
			err = sock->ops->listen(sock, backlog);                   /* 调用实际的listen函数 */

		fput_light(sock->file, fput_needed);
	}
	return err;
}
```



## vsock_listen函数

```c
static int vsock_listen(struct socket *sock, int backlog)
{
	int err;
	struct sock *sk;
	struct vsock_sock *vsk;

	sk = sock->sk;

	lock_sock(sk);

	if (sock->type != SOCK_STREAM) {             /* 确保是流套接字 */
		err = -EOPNOTSUPP;
		goto out;
	}

	if (sock->state != SS_UNCONNECTED) {         /* 确保sock状态是已连接 */
		err = -EINVAL;
		goto out;
	}

	vsk = vsock_sk(sk);

	if (!vsock_addr_bound(&vsk->local_addr)) {   /* 确保vsk已经bound */
		err = -EINVAL;
		goto out;
	}

	sk->sk_max_ack_backlog = backlog;
	sk->sk_state = TCP_LISTEN;                   /* 更改sk->sk_state为TCP_LISTEN */

	err = 0;

out:
	release_sock(sk);
	return err;
}
```
