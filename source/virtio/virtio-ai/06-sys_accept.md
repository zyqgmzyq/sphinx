# accept

### accept函数

```c
int s = socket(AF_VSOCK, SOCK_STREAM, 0);
memset(&addr, 0, sizeof(struct sockaddr_vm));
addr.svm_family = AF_VSOCK;
addr.svm_port = 9999;
addr.svm_cid = VMADDR_CID_HOST;

bind(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));

listen(s, 0);

struct sockaddr_vm peer_addr;
socklen_t peer_addr_size = sizeof(struct sockaddr_vm);
int peer_fd = accept(s, (struct sockaddr *)&peer_addr, &peer_addr_size);
```



## sys_accept函数

别的废话就不讲了，和前面bind类似。

```c
SYSCALL_DEFINE3(accept, int, fd, struct sockaddr __user *, upeer_sockaddr,
		int __user *, upeer_addrlen)
{
	return __sys_accept4(fd, upeer_sockaddr, upeer_addrlen, 0);
}

/*
 *	For accept, we attempt to create a new socket, set up the link
 *	with the client, wake up the client, then return the new
 *	connected fd. We collect the address of the connector in kernel
 *	space and move it to user at the very end. This is unclean because
 *	we open the socket then return an error.
 *
 *	1003.1g adds the ability to recvmsg() to query connection pending
 *	status to recvmsg. We need to add that support in a way thats
 *	clean when we restructure accept also.
 */

int __sys_accept4(int fd, struct sockaddr __user *upeer_sockaddr,
		  int __user *upeer_addrlen, int flags)
{
	struct socket *sock, *newsock;
	struct file *newfile;
	int err, len, newfd, fput_needed;
	struct sockaddr_storage address;

	if (flags & ~(SOCK_CLOEXEC | SOCK_NONBLOCK))
		return -EINVAL;

	if (SOCK_NONBLOCK != O_NONBLOCK && (flags & SOCK_NONBLOCK))
		flags = (flags & ~SOCK_NONBLOCK) | O_NONBLOCK;

	sock = sockfd_lookup_light(fd, &err, &fput_needed);    /* 根据fd找到对应的socket */
	if (!sock)
		goto out;

	err = -ENFILE;
	newsock = sock_alloc();                                /* 创建一个新的socket */
	if (!newsock)
		goto out_put;

	newsock->type = sock->type;                            /* 设置type和ops */
	newsock->ops = sock->ops;

	/*
	 * We don't need try_module_get here, as the listening socket (sock)
	 * has the protocol module (sock->ops->owner) held.
	 */
	__module_get(newsock->ops->owner);

	newfd = get_unused_fd_flags(flags);                     /* 为新的socket分配fd */
	if (unlikely(newfd < 0)) {
		err = newfd;
		sock_release(newsock);
		goto out_put;
	}
	newfile = sock_alloc_file(newsock, flags, sock->sk->sk_prot_creator->name);
	if (IS_ERR(newfile)) {
		err = PTR_ERR(newfile);
		put_unused_fd(newfd);
		goto out_put;
	}

	err = security_socket_accept(sock, newsock);         
	if (err)
		goto out_fd;

	err = sock->ops->accept(sock, newsock, sock->file->f_flags, false);  /* 调用实际的accept函数 */
	if (err < 0)
		goto out_fd;

	if (upeer_sockaddr) {
		len = newsock->ops->getname(newsock,
					(struct sockaddr *)&address, 2);
		if (len < 0) {
			err = -ECONNABORTED;
			goto out_fd;
		}
		err = move_addr_to_user(&address,
					len, upeer_sockaddr, upeer_addrlen);
		if (err < 0)
			goto out_fd;
	}

	/* File flags are not inherited via accept() unlike another OSes. */

	fd_install(newfd, newfile);
	err = newfd;

out_put:
	fput_light(sock->file, fput_needed);
out:
	return err;
out_fd:
	fput(newfile);
	put_unused_fd(newfd);
	goto out_put;
}
```



## vsock_accept函数

```c
static int vsock_accept(struct socket *sock, struct socket *newsock, int flags,
			bool kern)
{
	struct sock *listener;
	int err;
	struct sock *connected;
	struct vsock_sock *vconnected;
	long timeout;
	DEFINE_WAIT(wait);

	err = 0;
	listener = sock->sk;

	lock_sock(listener);

	if (sock->type != SOCK_STREAM) {     
		err = -EOPNOTSUPP;
		goto out;
	}

	if (listener->sk_state != TCP_LISTEN) {                        /* 确保sk_state是TCP_LISTEN */
		err = -EINVAL;
		goto out;
	}

	/* Wait for children sockets to appear; these are the new sockets
	 * created upon connection establishment.
	 */
	timeout = sock_sndtimeo(listener, flags & O_NONBLOCK);
	prepare_to_wait(sk_sleep(listener), &wait, TASK_INTERRUPTIBLE);

	while ((connected = vsock_dequeue_accept(listener)) == NULL &&   /* while循环等待client连接 */
	       listener->sk_err == 0) {
		release_sock(listener);
		timeout = schedule_timeout(timeout);
		finish_wait(sk_sleep(listener), &wait);
		lock_sock(listener);

		if (signal_pending(current)) {
			err = sock_intr_errno(timeout);
			goto out;
		} else if (timeout == 0) {
			err = -EAGAIN;
			goto out;
		}

		prepare_to_wait(sk_sleep(listener), &wait, TASK_INTERRUPTIBLE);
	}
	finish_wait(sk_sleep(listener), &wait);

	if (listener->sk_err)
		err = -listener->sk_err;

	if (connected) {
		listener->sk_ack_backlog--;

		lock_sock_nested(connected, SINGLE_DEPTH_NESTING);
		vconnected = vsock_sk(connected);

		/* If the listener socket has received an error, then we should
		 * reject this socket and return.  Note that we simply mark the
		 * socket rejected, drop our reference, and let the cleanup
		 * function handle the cleanup; the fact that we found it in
		 * the listener's accept queue guarantees that the cleanup
		 * function hasn't run yet.
		 */
		if (err) {
			vconnected->rejected = true;
		} else {
			newsock->state = SS_CONNECTED;               /* 更改sock状态为已连接 */
			sock_graft(connected, newsock);              /* 建立connected（sock）和 newsock（socket）对应关系，相互有指针指向对方； */
		}

		release_sock(connected);
		sock_put(connected);
	}

out:
	release_sock(listener);
	return err;
}
```
