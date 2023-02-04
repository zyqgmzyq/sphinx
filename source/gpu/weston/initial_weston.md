# Weston

## 调试weston（drm-backend）

```shell
sudo gdb -tui -args weston --tty 4
```



## 初始化weston

```c
// weston   executable.c
wet_main
    // 创建wl_display，在wayland-server.c实现
    wl_display_create                 
    
    // 获得display loop，在wayland-server.c实现
    wl_display_get_event_loop 
    
    // 把signal加入 event loop 的监听源  在event-loop.c
    wl_event_loop_add_signal
    
    // 选择backend
    weston_choose_default_backend
    
    // 创建weston_compositor
    weston_compositor_create
    
    // 加载backend
    load_backend
    
    weston_compositor_flush_heads_changed
    
    // 创建socket
    weston_create_listening_socket
    
    wet_load_shell

    // 唤醒compositor
    weston_compositor_wake
    
    // run display, 在wayland-server.c实现
    wl_display_run
```



## 创建weston_compositor

```c
// 创建weston_compositor对象，注册大量信号消息；创建各种global资源，创建图层layer，cursor_layer和fade_layer
weston_compositor_create
    weston_plane_init
    wl_display_init_shm
    // 创建定时器事件，定时器触发compositor中的idle_handler
    wl_event_loop_add_timer(loop, idle_handler, ec)
    // 创建定时器事件，定时器触发compositor中的output_repaint_timer_handler
    wl_event_loop_add_timer(loop, output_repaint_timer_handler,ec)
    // 初始化fade layer和cursor layer
    weston_layer_init
    // 设置fade layer和cursor layer的位置
    weston_layer_set_position
```



## 加载backend 

### load_backend

drm后端，是wayland环境中默认使用的后端，其使用Linux KMS输出，使用evdev作为输入，实际就是利用drm的接口实现合成。利用了硬件加速

```c
load_backend
	load_drm_backend
		// 设置wet_compositor.heads_changed_listener.notify 函数为 drm_heads_changed
		wet->heads_changed_listener.notify = drm_heads_changed
    	
    	// compositor加载backend
		weston_compositor_load_backend
    			weston_backend_init
    				drm_backend_create
                                
        // load remote output 如果没有remote-output  直接返回
		load_remoting    
```

### drm_backend_create

该函数设置drm backend的一系列回调函数，以及根据是否使用pixman初始化对应的绘图软件（pixman 或者 egl）

```c
static struct drm_backend *
drm_backend_create(struct weston_compositor *compositor,
		   struct weston_drm_backend_config *config)
{
	b->use_pixman = config->use_pixman;
	b->pageflip_timeout = config->pageflip_timeout;
	b->use_pixman_shadow = config->use_pixman_shadow;
	if (b->use_pixman) {
		if (init_pixman(b) < 0) {
			weston_log("failed to initialize pixman renderer\n");
			goto err_udev_dev;
		}
	} else {
		if (init_egl(b) < 0) {
			weston_log("failed to initialize egl\n");
			goto err_udev_dev;
		}
	}
    	b->base.destroy = drm_destroy;
	b->base.repaint_begin = drm_repaint_begin;
	b->base.repaint_flush = drm_repaint_flush;
	b->base.repaint_cancel = drm_repaint_cancel;
	b->base.create_output = drm_output_create;
	b->base.device_changed = drm_device_changed;
	b->base.can_scanout_dmabuf = drm_can_scanout_dmabuf;
    
	udev_input_init(&b->input,compositor, b->udev, seat_id, config->configure_device)
    
    drm_backend_create_heads(b, drm_device)
}
```

我们这里先主要看下init_egl函数具体干了点啥

```c
init_egl
    /* 创建gbm device  */
    b->gbm = create_gbm_device
        // 从gl-renderer.so加载gl_renderer
        gl_renderer = weston_load_module("gl-renderer.so", "gl_renderer_interface");
        // 创建gbm device
        gbm = gbm_create_device
    
    // drm-backend创建gl_renderer
    drm_backend_create_gl_renderer
```

接着继续看一下 drm_backend_create_gl_renderer，该接口会去调用libEGL提供的eglInitialize api;

```c
drm_backend_create_gl_renderer
	struct gl_renderer_display_options options = {
		.egl_platform = EGL_PLATFORM_GBM_KHR,
		.egl_native_display = b->gbm,
		.egl_surface_type = EGL_WINDOW_BIT,
		.drm_formats = format,
		.drm_formats_count = 2,
	};
	gl_renderer->display_create(b->compositor, &options)  // gl_renderer->display_create为gl_renderer_display_create
        gl_renderer_display_create   // 创建egl display
            gl_renderer_setup_egl_display
                eglInitialize        // 初始化egl display  在eglapi.c  （libEGL.so）
```

接着后面会创建drm_head并注册这个

```c
drm_backend_create_heads
	drm_head_create                    // 根据给定的drm connecotr创建一个drm head并且添加到weston head list
    	weston_compositor_add_head     // Register a new head
    		weston_compositor_schedule_heads_changed   // 把
```



### output初始化

首先要创建output

```c
weston_compositor_flush_heads_changed
	weston_compositor_call_heads_changed
		wl_signal_emit(&compositor->heads_changed_signal, compositor)
			drm_heads_changed   // 前面load_drm_backend设置heads_changed_listener.notify 函数为 drm_heads_changed
				drm_process_layoutputs
					drm_process_layoutput
    					wet_layoutput_create_output
    						weston_compositor_create_output
    							drm_output_create 
```

创建完output后需要attach head 到output

```c
drm_process_layoutput
    drm_try_attach
    	weston_output_attach_head
    		drm_output_attach_head
    
```

然后enable output

```c
weston_compositor_flush_heads_changed
	weston_compositor_call_heads_changed
		wl_signal_emit(&compositor->heads_changed_signal, compositor)
			drm_heads_changed   // 前面load_drm_backend设置heads_changed_listener.notify 函数为 drm_heads_changed
				drm_process_layoutputs
					drm_process_layoutput
						drm_try_attach_enable
							drm_backend_output_configure
							drm_try_enable
								weston_output_enable
									output->enabled
										drm_output_enable
```

先看下drm_output_enable大致都干了些啥

```c
static int drm_output_enable(struct weston_output *base)
{
    .......
    // 使用pixman
	if (b->use_pixman) {
		if (drm_output_init_pixman(output, b) < 0) {
			weston_log("Failed to init output pixman state\n");
			goto err;
		}
    // 使用egl
	} else if (drm_output_init_egl(output, b) < 0) {
		weston_log("Failed to init output gl state\n");
		goto err;
	}
    .......
    // 设置start_repaint_loop接口
    output->base.start_repaint_loop = drm_output_start_repaint_loop;
    // 设置repaint接口，用于最终绘制
    output->base.repaint = drm_output_repaint;
    output->base.assign_planes = drm_assign_planes;
    output->base.set_dpms = drm_set_dpms;
    output->base.switch_mode = drm_output_switch_mode;
    output->base.set_gamma = drm_output_set_gamma;
    
    .......
    return 0;
}
```

由于我们使用egl绘图，因此接着继续看一下drm_output_init_egl函数

```c
gl_renderer->output_window_create(&output->base, &options)
    gl_renderer_output_window_create                 // 创建egl surface
drm_output_init_cursor_egl
    gbm_bo_create                                    // 创建gbm buffer object  （libgbm.so）
    output->gbm_cursor_fb[i] = drm_fb_get_from_bo    // 获取drm_fb
```

## 创建socket

为wayland display创建socket,以便clients能够连接到这个socket;

wl_event_loop是weston的核心事件循环loop结构，wl_event_source是加入该loop等待weston处理的事件可以再细分为wl_event_source_fd 事件

```c
weston_create_listening_socket
    wl_display_add_socket
    	_wl_display_add_socket
    		wl_os_socket_cloexec    // 创建socket
    		// 创建了wl_event_source_fd，它代表一个基于socket fd的事件源
    		s->source = wl_event_loop_add_fd(display->loop, s->fd, WL_EVENT_READABLE, socket_data, display);    
```

wl_event_loop_add_fd函数的实现如下, 注意这个socket_data是被设置的回调函数,

```c
WL_EXPORT struct wl_event_source *
wl_event_loop_add_fd(struct wl_event_loop *loop, int fd, uint32_t mask, wl_event_loop_fd_func_t func, void *data)
{
	struct wl_event_source_fd *source;

	source = malloc(sizeof *source);
	if (source == NULL)
		return NULL;

	source->base.interface = &fd_source_interface;
	source->base.fd = wl_os_dupfd_cloexec(fd, 0);
	source->func = func;
	source->fd = fd;

	return add_source(loop, &source->base, mask, data);
}
```

将刚刚监听的fd通过add_source添加到display的loop->epoll_fd上，消息循环在上面等待client的连接。

当client端连接到server端的fd时，会调用处理函数wl_event_source_fd_dispatch()，该函数会调用之前注册的回调函数socket_data

其中socket_data的实现如下所示

```c
socket_data
    client_fd = wl_os_accept_cloexec   // 对client端的连接请求进行处理
    wl_client_create                   // 创建client对象，同时将该对象添加到compositor的client list中，那个时候，客户端已经初始化完成
```

wl_client_create函数具体实现

```c
wl_client_create
    // 将client_fd通过add_source添加到display的loop->epoll_fd上，消息循环在上面等待client的连接;注意
    // 设置的回调函数为wl_client_connection_data
    client->source = wl_event_loop_add_fd(display->loop, fd,
					      WL_EVENT_READABLE,
					      wl_client_connection_data, client);
    // 将display与client对象进行绑定
    bind_display(client, display) 
```

 着重看下bind_display函数，它将display与client对象进行绑定，当client端有display相关请求时，会调用client中的相关回调。实现如下：

```c
static int bind_display(struct wl_client *client, struct wl_display *display)
{
	client->display_resource =
		wl_resource_create(client, &wl_display_interface, 1, 1);
	if (client->display_resource == NULL) {
		/* DON'T send no-memory error to client - it has no
		 * resource to which it could post the event */
		return -1;
	}

	wl_resource_set_implementation(client->display_resource,
				       &display_interface, display,
				       destroy_client_display_resource);
	return 0;
}
```

 该函数首先创建了一个wl_resource类型对象，将值赋给client->display_resource。实际注册回调是在wl_resource_set_implementation。

```c
WL_EXPORT void
wl_resource_set_implementation(struct wl_resource *resource,
			       const void *implementation,
			       void *data, wl_resource_destroy_func_t destroy)
{
	resource->object.implementation = implementation;
	resource->data = data;
	resource->destroy = destroy;
	resource->dispatcher = NULL;
}
```

 其中display_interface封装的为对于request相关回调函数指针。

```c
static const struct wl_display_interface display_interface = {
	display_sync,
	display_get_registry
};
```

以上就是在启动wayland的server端时做的相关动作，而server端向client端发送event是通过wl_resource_post_event完成

### wet_load_shell

其实是调用一个client

```c
wet_load_shell  weston_view_create
    wet_shell_init
    	// 初始化text backend      是干啥用的？ 
    	text_backend_init
			launch_input_method	
    			weston_client_start
					weston_client_launch
    					wl_client_create
    	// 初始化weston layer
    	weston_layer_init
    	
    	// 创建weston desktop
    	weston_desktop_create 
    	
    	shell_fade_init
    		shell_fade_create_surface_for_output
```



### 唤醒compositor

```
weston_compositor_wake
```



## run display

```c
wl_display_run
	wl_display_flush_clients    // 将对应的out buffer通过socket发出去
	wl_event_loop_dispatch      // 处理消息循环
    	wl_event_loop_dispatch_idle 
    	wl_timer_heap_dispatch
```



![img](https://waynewolf.github.io/images/post/client-server-interaction.png)

![img](https://waynewolf.github.io/images/post/gles-egl-buffer-residence-and-init-sequence.png)
