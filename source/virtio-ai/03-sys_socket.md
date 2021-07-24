# socket

![image-20210715102744037](03-sys_socket.assets/image-20210715102744037.png)

## socket函数

 为了执行网络I/O，一个进程必须做的第一件事就是调用socket函数，指定期望的通信协议类型。该函数只是作为一个简单的接口函数供用户调用，调用该函数后将进入内核栈进行系统调用sock_socket 函数。

```c
/* 
 * 返回：非负描述字——成功， -1——出错
 * 其中family参数指明协议族，type参数指明套接口类型， 
 * 后面protocol通常设为0，以选择所给定family 和 type组合的系统缺省值
 */  
#include <sys/socket.h>
int socket(int family, int type, int protocol);

/* example */
socket(AF_VSOCK, SOCK_STREAM, 0);
```



## sock_socket函数

用户态程序调用socket函数，通过系统调用陷入内核。socket函数主要完成socket的创建，必要字段的初始化，关联传输控制块，绑定文件等任务，完成后返回socket绑定的文件描述符。用户态进入内核态是通过系统调用`sys_socket`实现，在内核中是通过`__sys_socket`函数实现其功能。

`SYSCALL_DEFINE3(socket, int, family, int, type, int, protocol)`最终会编译成`sys_socket`，`sys_socket`函数在`include\linux\syscalls.h`中的定义如下：

```c
/* net/socket.c */
asmlinkage long sys_socket(int, int, int);
```

`__sys_socket`函数主要工作如下：

1、`socket flags` 必要检查； 

2、调用`sock_create()`，新建一个socket结构体及相关内容 ； 

3、调用`sock_map_fd()`，新建一个struct file 并将file的`priv data`初始化为步骤2创建的socket，这样对文件的操作可以调用socket结构体定义的方法，并关联fd和file；

 4、返回fd 。

`__sys_socket`函数在4.19内核中的原型如下：

```c
int __sys_socket(int family, int type, int protocol)
{
	int retval;
	struct socket *sock;
	int flags;

	/* Check the SOCK_* constants for consistency.  */
	BUILD_BUG_ON(SOCK_CLOEXEC != O_CLOEXEC);
	BUILD_BUG_ON((SOCK_MAX | SOCK_TYPE_MASK) != SOCK_TYPE_MASK);
	BUILD_BUG_ON(SOCK_CLOEXEC & SOCK_TYPE_MASK);
	BUILD_BUG_ON(SOCK_NONBLOCK & SOCK_TYPE_MASK);

	flags = type & ~SOCK_TYPE_MASK;
	if (flags & ~(SOCK_CLOEXEC | SOCK_NONBLOCK))
		return -EINVAL;
	type &= SOCK_TYPE_MASK;

	if (SOCK_NONBLOCK != O_NONBLOCK && (flags & SOCK_NONBLOCK))
		flags = (flags & ~SOCK_NONBLOCK) | O_NONBLOCK;

	retval = sock_create(family, type, protocol, &sock);
	if (retval < 0)
		return retval;

	return sock_map_fd(sock, flags & (O_CLOEXEC | O_NONBLOCK));
}

SYSCALL_DEFINE3(socket, int, family, int, type, int, protocol)
{
	return __sys_socket(family, type, protocol);
}
```

可以看到，除去一些参数合法性校验，socket函数主要由`sock_create`和`sock_map_fd`这两个函数完成，下面分别看这两个函数。

### sock_create函数

`sock_create`函数主要由`__sock_create`函数来实现，主要工作为创建socket，并进行必要的初始化：

```c
int sock_create(int family, int type, int protocol, struct socket **res)
{
	return __sock_create(current->nsproxy->net_ns, family, type, protocol, res, 0);
}
EXPORT_SYMBOL(sock_create);
```

`__socket_create`函数主要工作如下：

1. domain域及协议合法性判断；
2. 调用`sock_alloc()` 分配一个`struct socket`结构体和`inode`，并且标明inode是socket类型，这样对inode的操作最终可以调用socket操作；
3. 根据输入参数，查找`net_families`数组(该数组通过inet_init创建)，获得域(比如inet，unix)特定的socket创建函数；
4. 调用实际create函数，对于inet域是`inet_create()`，对于vscok域是`vsock_create()`；

```c
int __sock_create(struct net *net, int family, int type, int protocol,
			 struct socket **res, int kern)
{
	int err;
	struct socket *sock;
	const struct net_proto_family *pf;

	/* Check protocol is in range */
	if (family < 0 || family >= NPROTO)
		return -EAFNOSUPPORT;
	if (type < 0 || type >= SOCK_MAX)
		return -EINVAL;

	/* Compatibility.

	   This uglymoron is moved from INET layer to here to avoid
	   deadlock in module load.
	 */
	if (family == PF_INET && type == SOCK_PACKET) {
		pr_info_once("%s uses obsolete (PF_INET,SOCK_PACKET)\n",
			     current->comm);
		family = PF_PACKET;
	}

	err = security_socket_create(family, type, protocol, kern);
	if (err)
		return err;

	/*
	 *	Allocate the socket and allow the family to set things up. if
	 *	the protocol is 0, the family is instructed to select an appropriate
	 *	default.
	 */
	sock = sock_alloc();	/* 创建struct socket结构体 */
	if (!sock) {
		net_warn_ratelimited("socket: no more sockets\n");
		return -ENFILE;	/* Not exactly a match, but its the
				   closest posix thing */
	}

	sock->type = type;	    /* 设置套接字类型*/

#ifdef CONFIG_MODULES
	/* Attempt to load a protocol module if the find failed.
	 *
	 * 12/09/1996 Marcin: But! this makes REALLY only sense, if the user
	 * requested real, full-featured networking support upon configuration.
	 * Otherwise module support will break!
	 */
	if (rcu_access_pointer(net_families[family]) == NULL)
		request_module("net-pf-%d", family);
#endif

	rcu_read_lock();
	pf = rcu_dereference(net_families[family]);	 /* 获取对应协议族的协议实例对象 */
	err = -EAFNOSUPPORT;
	if (!pf)
		goto out_release;

	/*
	 * We will call the ->create function, that possibly is in a loadable
	 * module, so we have to bump that loadable module refcnt first.
	 */
	if (!try_module_get(pf->owner))
		goto out_release;

	/* Now protected by module ref count */
	rcu_read_unlock();

	err = pf->create(net, sock, protocol, kern);  /* 调用实际create函数 */
	if (err < 0)
		goto out_module_put;

	/*
	 * Now to bump the refcnt of the [loadable] module that owns this
	 * socket at sock_release time we decrement its refcnt.
	 */
	if (!try_module_get(sock->ops->owner))
		goto out_module_busy;

	/*
	 * Now that we're done with the ->create function, the [loadable]
	 * module can have its refcnt decremented
	 */
	module_put(pf->owner);
	err = security_socket_post_create(sock, family, type, protocol, kern);
	if (err)
		goto out_sock_release;
	*res = sock;

	return 0;

out_module_busy:
	err = -EAFNOSUPPORT;
out_module_put:
	sock->ops = NULL;
	module_put(pf->owner);
out_sock_release:
	sock_release(sock);
	return err;

out_release:
	rcu_read_unlock();
	goto out_sock_release;
}
EXPORT_SYMBOL(__sock_create);
```

#### sock_alloc函数

`sock_alloc`函数分配一个`struct socket_alloc`结构体，将sockfs相关属性填充在`socket_alloc`结构体的`vfs_inode`变量中，以限定后续对这个sock文件允许的操作。同时`sock_alloc`最终返回`socket_alloc`结构体的socket变量，用于后续操作：

```c
struct socket *sock_alloc(void)
{
	struct inode *inode;
	struct socket *sock;

    /*创建inode和socket*/
	inode = new_inode_pseudo(sock_mnt->mnt_sb);
	if (!inode)
		return NULL;

    /*返回创建的socket指针*/
	sock = SOCKET_I(inode);

    /*inode相关初始化*/
	inode->i_ino = get_next_ino();
	inode->i_mode = S_IFSOCK | S_IRWXUGO;
	inode->i_uid = current_fsuid();
	inode->i_gid = current_fsgid();
	inode->i_op = &sockfs_inode_ops;

	return sock;
}
EXPORT_SYMBOL(sock_alloc);
```

#### pf->create函数

pf由`net_families[]`数组获得，`net_families[]`数组定义如下：

```c
/*
 *	The protocol list. Each protocol is registered in here.
 */
static DEFINE_SPINLOCK(net_family_lock);
static const struct net_proto_family __rcu *net_families[NPROTO] __read_mostly;
```

`net_families[]`数组的初始化在`__vsock_core_init`函数，

```c
static const struct net_proto_family vsock_family_ops = {
	.family = AF_VSOCK,
	.create = vsock_create,
	.owner = THIS_MODULE,
};

int __vsock_core_init(const struct vsock_transport *t, struct module *owner)
{
...
    err = sock_register(&vsock_family_ops);
...
}

int sock_register(const struct net_proto_family *ops)
{
...
    rcu_assign_pointer(net_families[ops->family], ops);
...
}
```

`net_families[]`数组里存放的是各个协议族的信息，以family字段作为下标。此处我们针对TCP协议分析，因此我们family字段是`AF_INET`，`pf->create`函数将调用`vsock_create`函数，该函数主要工作如下：

1. sock->state = SS_UNCONNECTED; //socket 状态设置
2. 调用__vsock_create函数

```c
static int vsock_create(struct net *net, struct socket *sock,
			int protocol, int kern)
{
	if (!sock)
		return -EINVAL;

	if (protocol && protocol != PF_VSOCK)
		return -EPROTONOSUPPORT;

	switch (sock->type) {
	case SOCK_DGRAM:
		sock->ops = &vsock_dgram_ops;
		break;
	case SOCK_STREAM:
		sock->ops = &vsock_stream_ops;
		break;
	default:
		return -ESOCKTNOSUPPORT;
	}

	sock->state = SS_UNCONNECTED;

	return __vsock_create(net, sock, NULL, GFP_KERNEL, 0, kern) ? 0 : -ENOMEM;
}
```

然后主要看下__vsock_create函数做了哪些事情：

1. 调用`sk_alloc()`，分配一个`struct sock`，并将proto类型的指针指向vsock_proto；
2. 调用`sock_init_data`，形成socket和sock一一对应的关系，相互有指针指向对方；
3. 初始化`vsock_sock`, `struct vsock_sock` 是`struct sock`的超集，具体参见`include/net/af_sock.h`中`vsock_sock`的定义；
4. 最后调用proto中注册的init函数，`transport->init(vsk, psk)`，这里是virtio-vsock,调用virtio_transport_do_socket_init函数；
5. 把vsk插入到bound_table的末尾；

```c
static struct proto vsock_proto = {
	.name = "AF_VSOCK",
	.owner = THIS_MODULE,
	.obj_size = sizeof(struct vsock_sock),
};

struct sock *__vsock_create(struct net *net,
			    struct socket *sock,
			    struct sock *parent,
			    gfp_t priority,
			    unsigned short type,
			    int kern)
{
	struct sock *sk;
	struct vsock_sock *psk;
	struct vsock_sock *vsk;

	sk = sk_alloc(net, AF_VSOCK, priority, &vsock_proto, kern);
	if (!sk)
		return NULL;

	sock_init_data(sock, sk);

	/* sk->sk_type is normally set in sock_init_data, but only if sock is
	 * non-NULL. We make sure that our sockets always have a type by
	 * setting it here if needed.
	 */
	if (!sock)
		sk->sk_type = type;

	vsk = vsock_sk(sk);
	vsock_addr_init(&vsk->local_addr, VMADDR_CID_ANY, VMADDR_PORT_ANY);
	vsock_addr_init(&vsk->remote_addr, VMADDR_CID_ANY, VMADDR_PORT_ANY);

	sk->sk_destruct = vsock_sk_destruct;
	sk->sk_backlog_rcv = vsock_queue_rcv_skb;
	sock_reset_flag(sk, SOCK_DONE);

	INIT_LIST_HEAD(&vsk->bound_table);
	INIT_LIST_HEAD(&vsk->connected_table);
	vsk->listener = NULL;
	INIT_LIST_HEAD(&vsk->pending_links);
	INIT_LIST_HEAD(&vsk->accept_queue);
	vsk->rejected = false;
	vsk->sent_request = false;
	vsk->ignore_connecting_rst = false;
	vsk->peer_shutdown = 0;
	INIT_DELAYED_WORK(&vsk->connect_work, vsock_connect_timeout);
	INIT_DELAYED_WORK(&vsk->pending_work, vsock_pending_work);

	psk = parent ? vsock_sk(parent) : NULL;
	if (parent) {
		vsk->trusted = psk->trusted;
		vsk->owner = get_cred(psk->owner);
		vsk->connect_timeout = psk->connect_timeout;
	} else {
		vsk->trusted = capable(CAP_NET_ADMIN);
		vsk->owner = get_current_cred();
		vsk->connect_timeout = VSOCK_DEFAULT_CONNECT_TIMEOUT;
	}

	if (transport->init(vsk, psk) < 0) {     /* virtio方式为virtio_transport_do_socket_init */
		sk_free(sk);
		return NULL;
	}

	if (sock)
		vsock_insert_unbound(vsk);

	return sk;
}
```



#### virtio_transport_do_socket_init函数

```c
int virtio_transport_do_socket_init(struct vsock_sock *vsk,
				    struct vsock_sock *psk)
{
	struct virtio_vsock_sock *vvs;

	vvs = kzalloc(sizeof(*vvs), GFP_KERNEL);   /* 创建 virtio_vsock_sock */
	if (!vvs)
		return -ENOMEM;

	vsk->trans = vvs;                          /* virtio_vsock_sock 和 vsock_sock 一一对应，有指针互相指向对方 */
	vvs->vsk = vsk;
	if (psk) {
		struct virtio_vsock_sock *ptrans = psk->trans;
		vvs->buf_size	= ptrans->buf_size;
		vvs->buf_size_min = ptrans->buf_size_min;
		vvs->buf_size_max = ptrans->buf_size_max;
		vvs->peer_buf_alloc = ptrans->peer_buf_alloc;
	} else {
		vvs->buf_size = VIRTIO_VSOCK_DEFAULT_BUF_SIZE;
		vvs->buf_size_min = VIRTIO_VSOCK_DEFAULT_MIN_BUF_SIZE;
		vvs->buf_size_max = VIRTIO_VSOCK_DEFAULT_MAX_BUF_SIZE;
	}

	vvs->buf_alloc = vvs->buf_size;

	spin_lock_init(&vvs->rx_lock);
	spin_lock_init(&vvs->tx_lock);
	INIT_LIST_HEAD(&vvs->rx_queue);

	return 0;
}
EXPORT_SYMBOL_GPL(virtio_transport_do_socket_init);
```



## sock_map_fd函数

`sock_map_fd`函数负责分配文件，并与socket进行绑定，主要做两件事：

1. 调用`sock_alloc_file`，分配一个`struct file`，并将私有数据指针指向socket结构；
2. `fd_install` 对应文件描述符和file。

```c
static int sock_map_fd(struct socket *sock, int flags)
{
	struct file *newfile;
    /*分配文件描述符*/
	int fd = get_unused_fd_flags(flags);
	if (unlikely(fd < 0)) {
		sock_release(sock);
		return fd;
	}

    /*分配file对象*/
	newfile = sock_alloc_file(sock, flags, NULL);
	if (likely(!IS_ERR(newfile))) {
		fd_install(fd, newfile);
		return fd;
	}

	put_unused_fd(fd);
	return PTR_ERR(newfile);
}
```

