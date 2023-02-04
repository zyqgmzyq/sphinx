# bind

【如何从用户态陷入到内核态】：https://ieevee.com/tech/2017/06/18/kernel-syscall.html

## bind函数

```c
int s = socket(AF_VSOCK, SOCK_STREAM, 0);

struct sockaddr_vm addr;
memset(&addr, 0, sizeof(struct sockaddr_vm));
addr.svm_family = AF_VSOCK;
addr.svm_port = 9999;
addr.svm_cid = VMADDR_CID_HOST;

bind(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));
```



## sys_bind函数

同创建socket一样，用户态程序调用bind函数，通过系统调用陷入内核。socket函数主要完成socket的创建，必要字段的初始化，关联传输控制块，绑定文件等任务，完成后返回socket绑定的文件描述符。用户态进入内核态是通过系统调用`sys_bind`实现，在内核中是通过`__sys_bind`函数实现其功能。

```c
/* 最终会编译成sys_bind */
SYSCALL_DEFINE3(bind, int, fd, struct sockaddr __user *, umyaddr, int, addrlen)  
{
	return __sys_bind(fd, umyaddr, addrlen);
}
```

__sys_bind函数主要工作如下：

1. 根据fd找到对应的socket对象；
2. 调用move_addr_to_kernel将用户态的地址拷贝内核中；
3. 通过找到的socket结构，调用socekt->ops->bind函数，进行地址绑定，返回到用户空间。

```c
int __sys_bind(int fd, struct sockaddr __user *umyaddr, int addrlen)
{
	struct socket *sock;
	struct sockaddr_storage address;
	int err, fput_needed;

	sock = sockfd_lookup_light(fd, &err, &fput_needed);          /* 根据fd找到对应的socket对象 */
	if (sock) {
		err = move_addr_to_kernel(umyaddr, addrlen, &address);   /* 将用户态的地址拷贝到内核中 */
		if (!err) {
			err = security_socket_bind(sock,
						   (struct sockaddr *)&address,
						   addrlen);
			if (!err)
				err = sock->ops->bind(sock,                      /* 调用实际的bind函数 */
						      (struct sockaddr *)
						      &address, addrlen);
		}
		fput_light(sock->file, fput_needed);
	}
	return err;
}
```



## vsock_bind函数

```c
static int
vsock_bind(struct socket *sock, struct sockaddr *addr, int addr_len)
{
	int err;
	struct sock *sk;
	struct sockaddr_vm *vm_addr;

	sk = sock->sk;

	if (vsock_addr_cast(addr, addr_len, &vm_addr) != 0)  /* 把sockaddr转换成sockaddr_vm */
		return -EINVAL;

	lock_sock(sk);
	err = __vsock_bind(sk, vm_addr);                     /* bind函数实现 */
	release_sock(sk);

	return err;
}

static int __vsock_bind(struct sock *sk, struct sockaddr_vm *addr)
{
	struct vsock_sock *vsk = vsock_sk(sk);
	u32 cid;
	int retval;

	/* First ensure this socket isn't already bound. */
	if (vsock_addr_bound(&vsk->local_addr))   
		return -EINVAL;

	/* Now bind to the provided address or select appropriate values if
	 * none are provided (VMADDR_CID_ANY and VMADDR_PORT_ANY).  Note that
	 * like AF_INET prevents binding to a non-local IP address (in most
	 * cases), we only allow binding to the local CID.
	 */
	cid = transport->get_local_cid();        /* 获取cid */
	if (addr->svm_cid != cid && addr->svm_cid != VMADDR_CID_ANY)
		return -EADDRNOTAVAIL;

	switch (sk->sk_socket->type) {           /* 分别根据是流套接字还是数据套接字调用对应的bind函数 */
	case SOCK_STREAM:
		spin_lock_bh(&vsock_table_lock);
		retval = __vsock_bind_stream(vsk, addr);
		spin_unlock_bh(&vsock_table_lock);
		break;

	case SOCK_DGRAM:
		retval = __vsock_bind_dgram(vsk, addr);
		break;

	default:
		retval = -EINVAL;
		break;
	}

	return retval;
}
```



## virtio_transport_get_local_cid函数

```c
static struct virtio_vsock *virtio_vsock_get(void)
{
	return the_virtio_vsock;     /* the_virtio_vsock是全局变量，在virtio_vsock_probe时候初始化 */
}

static u32 virtio_transport_get_local_cid(void)
{
	struct virtio_vsock *vsock = virtio_vsock_get();

	if (!vsock)
		return VMADDR_CID_ANY;

	return vsock->guest_cid;
}
```



## __vsock_bind_stream函数

```c
static int __vsock_bind_stream(struct vsock_sock *vsk,
			       struct sockaddr_vm *addr)
{
	static u32 port;
	struct sockaddr_vm new_addr;

	if (!port)
		port = LAST_RESERVED_PORT + 1 +
			prandom_u32_max(U32_MAX - LAST_RESERVED_PORT);

	vsock_addr_init(&new_addr, addr->svm_cid, addr->svm_port);  /* 初始化vsock addr */

	if (addr->svm_port == VMADDR_PORT_ANY) {
		bool found = false;
		unsigned int i;

		for (i = 0; i < MAX_PORT_RETRIES; i++) {
			if (port <= LAST_RESERVED_PORT)
				port = LAST_RESERVED_PORT + 1;

			new_addr.svm_port = port++;

			if (!__vsock_find_bound_socket(&new_addr)) {
				found = true;
				break;
			}
		}

		if (!found)
			return -EADDRNOTAVAIL;
	} else {
		/* If port is in reserved range, ensure caller
		 * has necessary privileges.
		 */
		if (addr->svm_port <= LAST_RESERVED_PORT &&
		    !capable(CAP_NET_BIND_SERVICE)) {
			return -EACCES;
		}

		if (__vsock_find_bound_socket(&new_addr))                         /* 从bound_table找合适bound的socket*/
			return -EADDRINUSE;
	}

	vsock_addr_init(&vsk->local_addr, new_addr.svm_cid, new_addr.svm_port);

	/* Remove stream sockets from the unbound list and add them to the hash
	 * table for easy lookup by its address.  The unbound list is simply an
	 * extra entry at the end of the hash table, a trick used by AF_UNIX.
	 */
	__vsock_remove_bound(vsk);                                           /* 先把vsk从bound_table的末尾移除掉 */
	__vsock_insert_bound(vsock_bound_sockets(&vsk->local_addr), vsk);    /* 把vsk插入到bound_table */

	return 0;
}
```

