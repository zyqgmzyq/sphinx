### git命令

```shell
配置
1. vim ~/.gitconfig
末尾添加：
[sendemail]
        smtpServer = smtp.huawei.com
        smtpUser = <工号>
        smtpServerPort = 25

2. vim ~/.bashrc
末尾添加：
function kpatch () {
   patch=$1
   shift
   git send-email $@ $patch \
   --cc-cmd="perl ./scripts/get_maintainer.pl --norolestats $patch" --to caojianlong@huawei.com
}

3. 拷贝 \\hghrnd-fs\hgh01\CRDU_Euler_F\61.哥德尔Lab\19 小组工作\AOS CARE\PEK-CERT组\小组协同
下的get_maintainer.pl 到你的pekse文件夹目录下的scripts文件夹（没有scripts文件夹，要先新建一个哈）

常用命令
1.创建补丁
git format-patch --subject-prefix="HM" -i HEAD~   一个commit使用
git format-patch --cover-letter --subject-prefix='HM] [PATCH' -N     多个commit使用

先检查patch文件：git apply --stat newpatch.patch
检查能否应用成功：git apply --check newpatch.patch
打补丁：git am --signoff < newpatch.patch

2.添加 Description
vim 000*.patch 
在Description字段添加描述：
包括以下几点：在做啥？ 为啥要做这个？具体怎么实现的？ 
最后添加MR链接

3.发送邮件
kpatch 000*.patch  --to caojianlong@huawei.com

git rebase --onto new_branch commit_id（开始移动的commit）
git commit --amend --author="Zhu Yaqin <zhuyaqin2@huawei.com>"
```





### 1.git基本语法

```shell
git clone <ssh url>                    # 克隆版本库  
git clone -b <branch name> <ssh url>   # 克隆指定分支
git add <filename>                     # 对文件添加跟踪 
git rm test.txt                        # 删除文件跟踪
git commit                             # 提交 
git commit --amend                     # 修改上一次提交的描述
git log                                # 查看提交 log
git reflog                             # 查看所有分支的所有操作记录
git status                             # 显示工作区和暂存区的状态
git config --global -l                 # 查看配置

git remote add yaqin <ssh url>         # 添加远程库并命名为 yaqin
git remote -v                          # 查看远程库
git fetch origin master:ue             # 拉取远程库
git pull origin master                 # 拉回远程版本库 origin 的 master 分支 
git remote remove [remote_name]        # 删除远程库 
git push origin --delete fecch -f      # 删除 yaqin 远程库的 fecch 分支
git push yaqin master:fecch -f         # 同步代码到远程仓库 yaqin( 从本地 master 分支到远程 fecch 分支)  
git config --global -l                 # 查看git配置
```



## 2.git分支

```shell
git branch                            # 列出分支清单 
git branch <your-branch-name>         # 创建新分支
git checkout <your-branch-name>       # 切换分支
git branch -D <your-branch-name>      # 删除分支
git checkout -b <your-branch-name>    # 创建分支并切换到该分支 
git branch -v                         # 查看各个分支最后一个提交对象的信息
git branch  --merge                   # 查看哪些分支已被并入当前分支 
```



合并分支

```shell
git merge  <branch-name>     # 从指定分支合并到当前分支
git rebase <branch-name>     # 取出一系列的提交记录，“复制”它们，然后在另外一个地方逐个的放下去。
```



## 3.版本回退

```shell
git reset <commit_id>   # 回退到 commit_id 提交节点，对本地库有效
git checkout .        # 回退本地所有修改而未提交的内容
git checkout  -filename  # 回退 filename文件本地所有修改而未提交的内容
git checkout <commit_id> # 回退到 commit_id 提交节点
git revert HEAD       # 对远程仓库有效
```



## 4.git自由修改提交树

```shell
git cherry-pick c1     # 将一些提交复制到当前所在的位置 
git rebase -i HEAD~4    # 选择某些提交或者对提交排序等 
```



## 5.git diff

```shell
git diff       # 显示工作目录(working tree)与索引区的文件变更(未被add的文件)
git diff --cached # 显示索引区和最后一次commit(HEAD)之间文件变更（已add但还未commit的文件）
dit diff HEAD    # 显示工作目录与最后一次commit之间的文件变更(所有未commit（包括未add和add两类）的文件)
git diff <master1> <master2> # 比较两个分支上最后 commit 的内容的差别
git diff <commit_id1><commit)id2> # 比较两个提交节点内容的差别
```



