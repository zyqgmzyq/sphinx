# start_kernel

```c
416 asmlinkage void __init start_kernel(void)
417 {
418         char * command_line;
419         extern struct kernel_param __start___param[], __stop___param[];
420 /*
421  * Interrupts are still disabled. Do necessary setups, then
422  * enable them
423  */
424         lock_kernel();
425         page_address_init();  /* 初始化高端内存（High Memory）线性地址空间中永久映射相关的全局变量 */
426         printk(linux_banner);
427         setup_arch(&command_line);
428         setup_per_cpu_areas();
429
430         /*
431          * Mark the boot cpu "online" so that it can call console drivers in
432          * printk() and can access its per-cpu storage.
433          */
434         smp_prepare_boot_cpu();
435
436         /*
437          * Set up the scheduler prior starting any interrupts (such as the
438          * timer interrupt). Full topology setup happens at smp_init()
439          * time - but meanwhile we still have a functioning scheduler.
440          */
441         sched_init();
442         /*
443          * Disable preemption - early bootup scheduling is extremely
444          * fragile until we cpu_idle() for the first time.
445          */
446         preempt_disable();
447         build_all_zonelists();
448         page_alloc_init();
449         printk("Kernel command line: %s\n", saved_command_line);
450         parse_early_param();
451         parse_args("Booting kernel", command_line, __start___param,
452                    __stop___param - __start___param,
453                    &unknown_bootoption);
454         sort_main_extable();
455         trap_init();
456         rcu_init();
457         init_IRQ();
458         pidhash_init();
459         init_timers();
460         softirq_init();
461         time_init();
462
463         /*
464          * HACK ALERT! This is early. We're enabling the console before
465          * we've done PCI setups etc, and console_init() must be aware of
466          * this. But we do want output early, in case something goes wrong.
467          */
468         console_init();
469         if (panic_later)
470                 panic(panic_later, panic_param);
471         profile_init();
472         local_irq_enable();
473 #ifdef CONFIG_BLK_DEV_INITRD
474         if (initrd_start && !initrd_below_start_ok &&
475                         initrd_start < min_low_pfn << PAGE_SHIFT) {
476                 printk(KERN_CRIT "initrd overwritten (0x%08lx < 0x%08lx) - "
477                     "disabling it.\n",initrd_start,min_low_pfn << PAGE_SHIFT);
478                 initrd_start = 0;
479         }
480 #endif
481         vfs_caches_init_early();
482         mem_init();
483         kmem_cache_init();
484         numa_policy_init();
485         if (late_time_init)
486                 late_time_init();
487         calibrate_delay();
488         pidmap_init();
489         pgtable_cache_init();
490         prio_tree_init();
491         anon_vma_init();
492 #ifdef CONFIG_X86
493         if (efi_enabled)
494                 efi_enter_virtual_mode();
495 #endif
496         fork_init(num_physpages);
497         proc_caches_init();
498         buffer_init();
499         unnamed_dev_init();
500         security_init();
501         vfs_caches_init(num_physpages);
502         radix_tree_init();
503         signals_init();
504         /* rootfs populating might need page-writeback */
505         page_writeback_init();
506 #ifdef CONFIG_PROC_FS
507         proc_root_init();
508 #endif
509         check_bugs();
510
511         acpi_early_init(); /* before LAPIC and SMP init */
512
513         /* Do the rest non-__init'ed, we're now alive */
514         rest_init();
```

