## build_all_zonelists

start_kernel --> build_all_zonelists

```c
1455 void __init build_all_zonelists(void)                                                                   1456 {                                                                                                       1457         int i;                                                                                         1458
1459         for_each_online_node(i)
1460                 build_zonelists(NODE_DATA(i));
1461         printk("Built %i zonelists\n", num_online_nodes());
1462 }
```

