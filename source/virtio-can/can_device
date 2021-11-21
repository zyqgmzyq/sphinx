# CAN

## 设备注册

设备注册有几个要点：

- flags设置
- netdev_ops设置，这个后面要详细讲
- 注册can设备

```c
int register_sja1000dev(struct net_device *dev)
{
	int ret;

	if (!sja1000_probe_chip(dev))
		return -ENODEV;

	dev->flags |= IFF_ECHO;	/* we support local echo */             
	dev->netdev_ops = &sja1000_netdev_ops;

	set_reset_mode(dev);
	chipset_init(dev);

	ret =  register_candev(dev);

	if (!ret)
		devm_can_led_init(dev);

	return ret;
}
EXPORT_SYMBOL_GPL(register_sja1000dev);
```

## sja1000_netdev_ops

```c
static const struct net_device_ops sja1000_netdev_ops = {
	.ndo_open	= sja1000_open,
	.ndo_stop	= sja1000_close,
	.ndo_start_xmit	= sja1000_start_xmit,
	.ndo_change_mtu	= can_change_mtu,
};
```

### sja1000_open

这里设置了中断函数，sja1000_interrupt

```c
static int sja1000_open(struct net_device *dev)
{
	struct sja1000_priv *priv = netdev_priv(dev);
	int err;

	/* set chip into reset mode */
	set_reset_mode(dev);

	/* common open */
	err = open_candev(dev);
	if (err)
		return err;

	/* register interrupt handler, if not done by the device driver */
	if (!(priv->flags & SJA1000_CUSTOM_IRQ_HANDLER)) {
		err = request_irq(dev->irq, sja1000_interrupt, priv->irq_flags,
				  dev->name, (void *)dev);
		if (err) {
			close_candev(dev);
			return -EAGAIN;
		}
	}

	/* init and start chi */
	sja1000_start(dev);

	can_led_event(dev, CAN_LED_EVENT_OPEN);

	netif_start_queue(dev);

	return 0;
}
```

### sja1000_start_xmit

发送数据

```c
static netdev_tx_t sja1000_start_xmit(struct sk_buff *skb,
					    struct net_device *dev)
{
	struct sja1000_priv *priv = netdev_priv(dev);
	struct can_frame *cf = (struct can_frame *)skb->data;
	uint8_t fi;
	uint8_t dlc;
	canid_t id;
	uint8_t dreg;
	u8 cmd_reg_val = 0x00;
	int i;

	if (can_dropped_invalid_skb(dev, skb))
		return NETDEV_TX_OK;

	netif_stop_queue(dev);

	fi = dlc = cf->can_dlc;
	id = cf->can_id;

	if (id & CAN_RTR_FLAG)
		fi |= SJA1000_FI_RTR;

	if (id & CAN_EFF_FLAG) {
		fi |= SJA1000_FI_FF;
		dreg = SJA1000_EFF_BUF;
		priv->write_reg(priv, SJA1000_FI, fi);
		priv->write_reg(priv, SJA1000_ID1, (id & 0x1fe00000) >> 21);
		priv->write_reg(priv, SJA1000_ID2, (id & 0x001fe000) >> 13);
		priv->write_reg(priv, SJA1000_ID3, (id & 0x00001fe0) >> 5);
		priv->write_reg(priv, SJA1000_ID4, (id & 0x0000001f) << 3);
	} else {
		dreg = SJA1000_SFF_BUF;
		priv->write_reg(priv, SJA1000_FI, fi);
		priv->write_reg(priv, SJA1000_ID1, (id & 0x000007f8) >> 3);
		priv->write_reg(priv, SJA1000_ID2, (id & 0x00000007) << 5);
	}

	for (i = 0; i < dlc; i++)
		priv->write_reg(priv, dreg++, cf->data[i]);

	can_put_echo_skb(skb, dev, 0);

	if (priv->can.ctrlmode & CAN_CTRLMODE_ONE_SHOT)
		cmd_reg_val |= CMD_AT;

	if (priv->can.ctrlmode & CAN_CTRLMODE_LOOPBACK)
		cmd_reg_val |= CMD_SRR;
	else
		cmd_reg_val |= CMD_TR;

	sja1000_write_cmdreg(priv, cmd_reg_val);

	return NETDEV_TX_OK;
}
```

### sja1000_interrupt

接收数据

```c
irqreturn_t sja1000_interrupt(int irq, void *dev_id)
{
	struct net_device *dev = (struct net_device *)dev_id;
	struct sja1000_priv *priv = netdev_priv(dev);
	struct net_device_stats *stats = &dev->stats;
	uint8_t isrc, status;
	int n = 0;

	if (priv->pre_irq)
		priv->pre_irq(priv);

	/* Shared interrupts and IRQ off? */
	if (priv->read_reg(priv, SJA1000_IER) == IRQ_OFF)
		goto out;

	while ((isrc = priv->read_reg(priv, SJA1000_IR)) &&
	       (n < SJA1000_MAX_IRQ)) {

		status = priv->read_reg(priv, SJA1000_SR);
		/* check for absent controller due to hw unplug */
		if (status == 0xFF && sja1000_is_absent(priv))
			goto out;

		if (isrc & IRQ_WUI)
			netdev_warn(dev, "wakeup interrupt\n");

		if (isrc & IRQ_TI) {
			/* transmission buffer released */
			if (priv->can.ctrlmode & CAN_CTRLMODE_ONE_SHOT &&
			    !(status & SR_TCS)) {
				stats->tx_errors++;
				can_free_echo_skb(dev, 0);
			} else {
				/* transmission complete */
				stats->tx_bytes +=
					priv->read_reg(priv, SJA1000_FI) & 0xf;
				stats->tx_packets++;
				can_get_echo_skb(dev, 0);
			}
			netif_wake_queue(dev);
			can_led_event(dev, CAN_LED_EVENT_TX);
		}
		if (isrc & IRQ_RI) {
			/* receive interrupt */
			while (status & SR_RBS) {
				sja1000_rx(dev);
				status = priv->read_reg(priv, SJA1000_SR);
				/* check for absent controller */
				if (status == 0xFF && sja1000_is_absent(priv))
					goto out;
			}
		}
		if (isrc & (IRQ_DOI | IRQ_EI | IRQ_BEI | IRQ_EPI | IRQ_ALI)) {
			/* error interrupt */
			if (sja1000_err(dev, isrc, status))
				break;
		}
		n++;
	}
out:
	if (priv->post_irq)
		priv->post_irq(priv);

	if (n >= SJA1000_MAX_IRQ)
		netdev_dbg(dev, "%d messages handled in ISR", n);

	return (n) ? IRQ_HANDLED : IRQ_NONE;
}
```

