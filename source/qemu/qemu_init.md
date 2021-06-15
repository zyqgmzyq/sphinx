# 初始化

## main函数

```c
main
	qemu_init
	qemu_main_loop
	qemu_cleanup
```

## qemu_init
### 执行qom init函数

先调用 module_call_init(MODULE_INIT_QOM) 函数，查这个MODULE_INIT_QOM类型的QTAIL链表，找到其对应的所有init函数，执行所有与其挂接的init函数

以cpu初始化为例，执行arm_cpu_register_types函数

```c
arm_cpu_register_types
	type_register_static(&arm_cpu_type_info);
	type_register_static(&host_arm_cpu_type_info);
	arm_cpu_register(&arm_cpus[i]);
```

以virt机器为例，那么就会执行machvirt_machine_init函数，

```c
main
	qemu_init
    	module_call_init(MODULE_INIT_QOM) 
            machvirt_machine_init
                type_register_static(&virt_machine_info);
                    type_register(info);
                        type_register_internal(info);
                            ti = type_new(info);   // 根据info信息，创建一个TypeImpl对象
                            type_table_add(ti);    // 将ti插入一个hash表中(第一次调用会新建hash表)。这个表中就存储了各种不同类型cpu的信息:name, parent,class_init,instance_init
```

然后就是解析参数,详见参数解析那一章好了~

根据传入的-m参数设置ramsize

```c
set_memory_options
    qemu_opt_get_size   // 获取-m传入的size并赋值给ram_size
    
current_machine->ram_size = ram_size;         // 传入的size
current_machine->maxram_size = maxram_size;   // 传入的size
current_machine->ram_slots = ram_slots;       // 0
```

### select_machine

```c
qemu_init
	select_machine
    	optarg = qemu_opt_get(opts, "type");              /* 获取machine type （virt）*/
		machine_class = machine_parse(optarg, machines);  /* 获取对应的machine class */
```

### machine_class_init

根据用户输入的machine type参数，选择对应的machine class ，并调用machine_class_init函数

```c
qemu_init
    select_machine
		object_class_get_list
			object_class_foreach	
    			g_hash_table_foreach
    				object_class_foreach_tramp
    					type_initialize
							virt_machine_class_init
```


### machine_instance_init

根据machine class创建machine instance实例，调用machine_instance_init函数并进行初始化

```c
qemu_init
	object_new_with_class
		object_new_with_type
			object_init_with_type
				virt_instance_init
```

解析传入的kernel等参数

```c
kernel_filename = qemu_opt_get(machine_opts, "kernel");
initrd_filename = qemu_opt_get(machine_opts, "initrd");
kernel_cmdline = qemu_opt_get(machine_opts, "append");
```

### machine_run_board_init

根据传入的current_machine，调用对应machine的mach_board_init 函数

```c
qemu_init
    machine_runmachvirt_init_board_init
		machvirt_init
```


初始化virt_firmware_init

create gic,uart，mmio等硬件信息

然后调用arm_load_kernel函数

## main_loop_wait

```c
qemu_main_loop     // 主线程开启循环，监听事件

machine_run_board_init
```

