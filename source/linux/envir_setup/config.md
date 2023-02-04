## 创建用户

```shell
sudo adduser zyq
sudo usermod -aG sudo zyq
```

## 升级vim

```shell
# 下载vim源码
./configure --enable-python3interp=yes --with-x
make -j16 && sudo make install
sudo rm /usr/bin/vim
sudo ln -sv /usr/local/bin/vim /usr/bin/vim
```

Error：configure: error: could not configure X

解决：sudo apt-get install libxt-dev
sudo apt-get install libgtk2.0-dev
rm -rf src/auto/config.cache

## samba配置

```shell
sudo apt-get install samba

# 创建samba用户
# 注意，创建samba用户之前，必须先确保有一个同名的Linux用户，否则samba用户会创建失败。
sudo smbpasswd -a smbuser

# 重启服务
sudo service smbd restart

# /etc/samba/smb.conf文件添加以下内容
[share]
   comment = share directory 
   path = /home/zyq/share 
   available = yes
   valid user= zyq 
   writable = yes
```

Error：internal compiler error: Killed (program cc1plus)

```
sudo swapoff -a
sudo fallocate -l 10G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo cp /etc/fstab /etc/fstab.bak
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

