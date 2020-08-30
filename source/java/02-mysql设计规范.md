# 数据库设计规范

## 1 必须遵守

库名、表名、字段名、索引名必须使用小写字母，并且不能以Mysql关键字&保留字命名 [Mysql 5.7](https://dev.mysql.com/doc/refman/5.7/en/keywords.html)

所有表必须又INT/BIGINT unsigned NOT NULL AUTO_INCREMENT 类型的主键，提高顺序insert效率，强烈建议该列与业务没有联系，并且不建议使用组合主键，仅仅作为自增主键id使用

1. 当表的预估数量在42亿条以内，请使用INT UNSIGNED
2. 当表的预估数量超过42亿条，请使用BIGINT UNSIGNED
3. 不建议一张表存42亿数据

**【为什么InnoDB表建议用自增列做主键】[为什么InnoDB表建议用自增列做主键](https://imysql.com/2014/09/14/mysql-faq-why-innodb-table-using-autoinc-int-as-pk.shtml)**

1. InnoDB引擎表是基于B+树的索引组织结构（IOT）
2. 每个表都需要有一个聚簇索引（cluster index）
3. 所有的行记录都存储在B+数的叶子节点（leaf pages of the tree）
4. 基于聚簇索引的增删改查的效率相对是最高的
5. 如果我们定义了主键（Primary key），那么InnoDB会选择其作为聚集索引
6. 如果没有显式定义主键，则InnoDB会选择第一个不包含NULL值的唯一索引作为主键索引
7. 如果也没有这样的唯一索引，则InnoDB会选择内置6字节长的ROWID作为隐含的聚集索引（ROWID随着行记录的写入而主键递增，这个ROWID不像ORACLE的ROWID那样可引用，是隐含的）

综上所述，如果InnoDB表的数据写入顺序能和B+树索引的叶子节点顺序一致的话，这时候存取效率是最高的，也就是下面这几种情况的存取效率最高：

1. 使用自增列（INT/BIGINT类型）做主键，这时候写入顺序是自增的，和B+数叶子节点分裂顺序一致
2. 该表不指定自增列做主键，同时也没有可以被选为主键的唯一索引，这时候InnoDB会选择内置的ROWID作为主键，写入顺序和ROWID增长顺序一致
3. 除此之外，如果一个InnoDB表又没有显示主键，又有可以被选择为主键的唯一索引，但该唯一索引可能不是递增关系时（例如字符串，UUID，多字段联合唯一索引的情况），该表的存取效率就会比较差

**总结：**

1. 主键自增，数据行写入可以提高插入性能，可以避免page分裂，减少表碎片提升空间和内存的使用
2. 自增型主键设计（int，bigint）可以降低二级索引的空间，提升二级索引的内存命中率
3. 主键要选择较短的数据类型，InnoDB引擎普通索引都会保存主键的值，较短的数据类型可以有效减少索引的磁盘空间，提高索引的缓存效率
4. 无主键的表删除，在row模式的主从架构，会导致备库夯住

所有的字段都是必须用NOT NULL DEFAULT 属性，避免字段存在NULL值，不便于计算与比较

1. 数值类型使用：NOT NULL DEFAULT 0
2. 字符类型使用：NOT NULL DEFAULT ""

**特别注意**：timestamp类型不指定默认值的话，MariaDB会默认给0；对于一个timestamp字段没有指定默认值，会自动给一个timestamp默认值为CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP，其他为0

**【为什么使用NOT NULL属性】**

1. NULL的列使得索引/索引统计/值比较都更加复杂，对Mysql来说更难优化
2. NULL这种类型Mysql内部需要进行特殊处理，增加数据库处理记录的复杂性；同等条件下，表中有较多空字段的时候，数据库的处理性能会降低很多
3. NULL值需要更多的存储空间，无论是表还是索引中每行中的NULL的列都需要额外的空间来标识
4. 对NULL处理的时候，只能采用is null或is not null，而不能采用=、in、<、<>、!=、not in 这些操作符号。如：where name!="name"，如果存在name为null值的记录，查询结果就不会包含name为null值的记录

Mysql中的NULL其实是占用空间的，空值是不占空间的

```
NULL columns require additional space in the row to record whether their values are NULL. For MyISAM tables, each NULL column takes one bit extra, rounded up to the nearest byte.
```

NOT NULL 不能插入NULL值，可以插入空值，NULL其实不是空值，而是要占用空间的，所以mysql在进行比较的时候，NULL会参与字段比较，所以对效率有一部分影响，而且B树索引时不会存储NULL值，所以如果所以的字段可以为NULL，索引的效率会下降很多

is not null 取出的是非NULL的记录

<> 取出的是空值记录

**【注意】**

1. 在进行count()统计某列的记录数的时候，如果采用的NULL值，系统会自动忽略掉，但是空值是会进行统计到其中的
2. 判断NULL用is_null或者is not null，sql语句函数中可以使用if null()函数来进行处理，判断空字符用=''或者<>''来进行处理
3. 对于Mysql特殊的注意事项，对于timestamp数据类型，如果往这个数据类型插入的列插入NULL值，则出现的值是当前的系统时间。插入空值，则会出现0000-00-00 00:00:00
4. 对于空值的判断到底用is null还是=''，要根据实际业务来进行区分

所有表必须携带ctime（创建时间），mtime（最后修改时间）这两个字段，便于数据分析以及故障排查

```sql
#两个字段的类型如下，只需要在建表时建立即可，不需要开发人员再往其中插入时间值，前提是INSERT INTO语句显示的字段名称：
ctime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
mtime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间'
```

1. 所有表以及字段必须添加Comment，方便自己和他人阅读，一段时间之后可能自己都不知道这些没有加Comment的字段是干什么的
2. 非唯一索引按照"ix字段名称"进行命名，如ix_uid_name
3. 唯一索引按照“uk字段名称”进行命名，如uk_uid_name
4. Join查询时，用于Join的字段定义必须完全相同（避免隐式转换），并且建立索引
5. 存储单个IP时，必须使用整型INT UNSIGNED类型，不允许使用字符型VARCHAR()存储单个IP
6. 时间类型，首选使用整型INT、INT UNSIGNED类型，其次使用DATETIME类型
7. 日期类型，请使用date类型
8. 所有表必须将mtime增加一个普通索引ix_mtime（mtime），便于数据平台、AI、搜索部门增量获取数据

```
INT: 存储范围：-2147483648 to 2147483647 对应的时间范围: 1970/1/1 8:00:00 – 2038/1/19 11:14:07
INT UNSIGNED: 存储范围：0 to 4294967295 对应的时间范围：1970/1/1 8:00:00 – 2106/2/7 14:28:15
```

## 2 强烈建议

1. 涉及精确金额相关的字段类型，强烈建议扩大N倍后转换成整型存储（例如金额中的分扩大百倍后存储成整型），避免浮点数加减出现不准确的问题，也强烈建议比实际需求多保留一位，便于后续财务方面对账更加准确

2. 对于CHAR(N)/VARCHAR(N)类型，在满足够用的前提下，尽可能小的选择N的大小，并且建议N<255，用于节省磁盘空间和内存空间

3. ```
   # 自动插入默认时间类型，多用于创建时间类型
   ctime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
   # 自动插入默认时间且随着记录的更新而更新，多用于更新时间类型
   mtime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
   # 程序不指定时间的前提下，插入'0000-00-00 00:00:00'，且不随着记录的更新而更新，多用于单纯的记录时间
   dt DATETIME NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT '记录时间'
   ```

4. 强烈建议使用TINYINT代替ENUM类型，新增ENUM类型需要在DDL操作，对于TINYINT类型在数据库字段Comment和程序代码中做好备注信息，避免混淆，如：

5. ```sql
   # 错误示例，使用enum类型
   mysql> create  table t(id int not null auto_increment primary key comment '自增ID',num enum('0','1','2','3') comment 'enum枚举类型' );
   Query OK, 0 rows affected (0.01 sec)
   mysql> insert into t(num) values(1);
   Query OK, 1 row affected (0.00 sec)
   mysql> select * from t;
   +----+------+
   | id | num  |
   +----+------+
   |  1 | 0    |
   +----+------+
   1 row in set (0.00 sec)
   mysql> insert into t(num) values('1');
   Query OK, 1 row affected (0.00 sec)
   mysql> select * from t;
   +----+------+
   | id | num  |
   +----+------+
   |  1 | 0    |
   |  2 | 1    |
   +----+------+
   2 rows in set (0.00 sec)
   # 正确示例，使用TINY类型
   `num` tinyint(4) NOT NULL DEFAULT '0' COMMENT 'TINY枚举类型：0-不通过，1-通过'
   ```

6. 强烈建议不要再数据库中进行排序，特别是大数据量的排序，可考虑再程序中设计排序

7. 强烈建议不要对数据做真正意义上的物理删除（DELETED），可考虑逻辑删除，即在表中设计一个is_deleted字段标记该字段是否删除，防止毁灭性事件的发生

8. 强烈建议每张表数据量控制在千万级别以下，如果预估超过千万级别，请在设计时考虑归档，日志系统，数据分析平台等方案

9. 强烈建议索引选择时，WHERE条件中并不是所有的列都适合作为索引列，组合索引尽量将区分度高以及使用频率高的字段优先放在前面，如“性别”由于区分度太小则不适合做索引

## 3 尽量避免

1. 尽量避免使用BLOB，TEXT类型的字段，超大文件建议使用对象存储，在mysql中只保存路径，隐患如下：
   1. 会浪费更多的磁盘和内存空间，非必要的大量的大字段查询会淘汰掉热数据，导致内存命中率急剧降低，影响数据库的性能
   2. 该表在相同的QPS下会消耗正常表N倍的磁盘IO和网络IO资源，当IO被打满之后，会影响到当前服务器上的所有数据库稳定性
   3. 如果必须使用，请与主表拆开，使用主键进行关联
   4. 如果必须使用，请控制QPS在100以内
2. 尽量避免使用浮点型类型，计算机处理整型比浮点型快N倍，如果必须使用，请将浮点型扩大N倍后转为整型
3. 尽量避免在数据库中做计算，减轻数据库压力
4. 尽量避免Join查询，请尽可能地使用单表查询，减少查询复杂度，减轻数据库压力

## 4 绝对禁止

1. 生产环境中，表一旦设计好，字段只允许增加（ADD COLUMN），禁止减少（DROP COLUMN），禁止改名称（CHANGE/MODIFY COLUMN）

2. 禁止使用update...limit...和deleted...limit...操作，因为你无法得知自己究竟更新或者删除了哪些数据，请务必添加ORDER BY进行排序，如：

3. ```sql
   # 这是错误的语法示例
   UPDATE tb SET col1=value1 LIMIT n;
   # 这是错误的语法示例
   DELETE FROM tb LIMIT n;
   # 这是正确的语法示例
   UPDATE tb SET col1=value1 ORDER BY id LIMIT n;
   # 这是正确的语法示例
   DELETE FROM tb ORDER BY id LIMIT n;
   ```

4. 禁止超过2张表的JOIN查询

5. 禁止使用子查询，如：

6. ```sql
   # 这是错误的语法示范
   SELECT col1,col2 FROM tb1 WHERE id IN (SELECT id FROM tb2);
   ```

7. 禁止回退表的DDL操作

8. 禁止在数据库中使用视图、存储过程、函数、触发器、事件

9. 禁止出现冗余索引，如索引(a)，索引(a,b)，此时索引(a)为冗余索引

10. 禁止使用外键，外键的逻辑应当由程序去控制

    1. ```
       外键会导致表与表之间耦合，UPDATE与DELETE操作都会涉及相关联的表，十分影响SQL 的性能，甚至会造成死锁。高并发情况下容易造成数据库性能，大数据高并发业务场景数据库使用以性能优先.
       ```

11. 禁止使用order by rand()排序，性能极其低下

## 5 语句书写规范

### 5.1 create table 语句

```sql
# 这是正确的语法示范
CREATE TABLE `User` (
  `c1` int(11) NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
  `c2` int(11) NOT NULL DEFAULT '0' COMMENT '无符号数值型字段',
  `c3` int(11) NOT NULL DEFAULT '0' COMMENT '有符号数值型字段',
  `c4` varchar(16) NOT NULL DEFAULT '0' COMMENT '变长字符型字段',
  `ctime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间类型字段',
  `mtime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间类型字段',
  `c7` tinyint(4) NOT NULL DEFAULT '0' COMMENT '枚举类型字段：0-xxx,1-xxx,2-xxx',
  PRIMARY KEY (`c1`),
  UNIQUE KEY `uk_c2` (`c2`),
  KEY `ix_c3` (`c3`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='天马物料表'
```

### 5.2 alter table 语句

#### 5.2.1 添加字段

```sql
# 这是正确的语法示范
ALTER TABLE User ADD COLUMN c8 int(11) NOT NULL DEFAULT 0 COMMENT '添加字段测试';
# 添加字段时禁止使用after/before属性，避免数据偏移。
```

#### 5.2.2 变更字段

```sql
# 这是正确的语法示范
# MODIFY只修改字段定义（优先使用）
ALTER TABLE User MODIFY COLUMN c8 varchar(16) NOT NULL DEFAULT 0 COMMENT 'MODIFY修改字段定义';
# CHANGE修改字段名称
ALTER TABLE User CHANGE COLUMN c7 c8 varchar(16) NOT NULL DEFAULT 0 COMMENT 'CHANGE修改字段名称';
```

#### 5.2.3 添加主键

```sql
# 这是正确的语法示范
ALTER TABLE  User ADD PRIMARY KEY(c1);
```

#### 5.2.4 删除字段（不要想不开）

```sql
# 这是正确的语法示范
ALTER TABLE User DROP COLUMN c8;
```

#### 5.2.5 删除主键（不要想不开）

```sql
# 这是正确的语法示范
ALTER TABLE User DROP PRIMARY KEY;
```

DDL最好写到一个sql里面，否则表会重建N次。DBA使用工具，最好将对同一个表的DDL都写到一个sql里面，不会涉及到锁升级

### 5.3 create/drop index语句

1. 索引升序asc，降序desc

   1. mariadb暂时不支持降序索引desc，之所以能创建成功是因为其将desc设置为关键字，实际上仍然是asc索引

2. 添加普通索引

   1. ```sql
      # 这是正确的语法示范
      alter table tb1 add INDEX ix_c3(c3);
      
       tips：如果创建的是联合索引，筛选度高的列靠左
      ```

3. 添加唯一索引

   1. ```sql
      # 这是正确的语法示范
      alter table tb1 add UNIQUE INDEX uk_c2(c2);
      ```

4. 删除普通索引

   1. ```sql
      # 这是正确的语法示范
      alter table tb1 DROP INDEX ix_c3;
      ```

5. 删除唯一索引

   1. ```sql
      # 这是正确的语法示范
      alter table tb1 DROP INDEX uk_c2;
      ```

### 5.4 select 语句

1. 禁止使用SELECT * FROM 语句，SELECT只需要获取的字段，既防止了新增字段对程序应用的逻辑的影响，又减少了程序和数据库的性能影响

   1. ```sql
      # 这是错误的语法示范
      SELECT * FROM tb WHERE col1=value1;
      # 这是正确的语法示范
      SELECT col1,col2 FROM tb WHERE col1=value1;
      ```

2. 合理的使用数据类型，避免出现隐式转换，隐式转换无法使用索引且效率低，如：`SELECT name FROM tb WHERE id='1';`,此时id为int类型，此时出现隐式转换［这是错误的语法示范］

3. 不建议使用％前缀模糊查询，导致查询无法使用索引，如：`SELECT id FROM tb WHERE name LIKE '%User';`［这是错误的语法示范］；

4. 对于LIMIT操作，强烈建议使先ORDER BY 再LIMIT，即`ORDER BY c1 LIMIT n`；

### 5.5 insert语句

```sql
# INSERT INTO语句的正确语法示例
INSERT INTO tb(col1,col2) VALUES(value1,values2);
```

1. INSERT INTO语句需要显示指明字段名称;
2. 对于多次单条INSERT INTO语句，务必使用批量INSERT INTO语句，提高INSERT INTO语句效率，如：

```sql
# 多次单条INSERT INTO，这是错误的语法示例
INSERT INTO tb(col1,col2) VALUES(value1,values2);
INSERT INTO tb(col1,col2) VALUES(value3,values4);
INSERT INTO tb(col1,col2) VALUES(value5,values6);
# 批量INSERT INTO语句，这是正确的语法示例
INSERT INTO tb(col1,col2) VALUES(value1,values2),(value3,values4),(value5,values6);
```

### 5.6 update语句

```sql
# UPDATE语句的正确语法示例
UPDATE tb SET col1=value1,col2=value2,col3=value3 WHERE col0=value0 AND col5=value5;
```

1. 注意：SET后接的并列字段分隔符为”逗号(,)”，而不是常见的”AND”，使用”AND”也能将UPDATE语句执行成功，但意义完全不一样，详情请戳：
2. 强烈建议UPDATE语句后携带WHERE条件，防止灾难性事件的发生；
3. 如果需要使用UPDATE修改大量数据时，请联系DBA协助处理，该语句极易引起主从复制延迟；
4. 禁止使用`UPDATE ... LIMIT ...`语法，详情请看第1.4条规范。

### 5.7 DELETE语句

```sql
# DELETE语句的正确语法示例
DELETE FROM tb WHERE col0=value0 AND col1=value1;
```

1. 强烈建议deleted语句后携带where条件，防止灾难性事件的发生
2. 如果需要使用deleted语句大量删除数据时，联系DBA处理，该语句极易引起主从复制延迟
3. 禁止使用delete...limit...语法

## 6 其他书写规范

1. 禁止在字段上使用函数

   1. ```sql
      # 这是错误的语法示范
      SELECT col1,col2 FROM tb WHERE unix_timestamp(col1)=value1;
      # 这是正确的语法示范
      SELECT col1,col2 FROM tb WHERE col1=unix_timestamp(value1);
      ```

2. 强烈建议字段放在操作符左边

   1. ```sql
      # 这是错误的语法示范
      SELECT col1,col2 FROM tb WHERE value1=col1l
      # 这是正确的语法示范
      SELECT col1,col2 FROM tb WHERE col1=value1;
      ```

3. 禁止将字符类型传入到整型类型字段中，也禁止整形类型传入到字段类型中，存在隐式转换的问题

   1. ```sql
      # 这是错误的语法示范
      # var_col字段为VARCHAR类型
      SELECT col1,col2 FROM tb WHERE var_col=123;
      # int_col字段为INT类型
      SELECT col1,col2 FROM tb WHERE int_col='123';
      # 这是正确的语法示范
      # var_col字段为VARCHAR类型
      SELECT col1,col2 FROM tb WHERE var_col='123';
      # int_col字段为INT类型
      SELECT col1,col2 FROM tb WHERE int_col=123;
      ```

## 7 程序操作数据库设置规范

### 7.1 必须遵守

1. 如果应用使用的是长连接，应用必须具有自动重连的机制，但请避免每执行一个SQL去检查一次DB可用性；
2. 如果应用使用的是长连接，应用应该具有连接的TIMEOUT检查机制，及时回收长时间没有使用的连接，TIMEOUT时间一般建议为2小时；
3. 程序访问数据库连接的字符集请设置为utf8mb4；

### 7.2 绝对禁止

1. 程序中禁止一切DDL操作

### 7.3 行为规范

1. 禁止使用应用程序配置文件内的帐号手工访问线上数据库，大部分配置文件内的数据库配置的是主库，你无法预知你的一条SQL会不会导致MySQL崩溃；
2. 大型活动(如拜年祭) 或 突发性大量操作数据库(如发送私信)等操作时，应提前与DBA当面沟通，进行流量评估，避免数据库出现瓶颈；
3. 批量清洗数据，需要开发和DBA共同进行审查，应避开业务高峰期时段执行，并在执行过程中观察服务状态；
4. 禁止在主库上执行后台管理和统计类的功能查询，这种复杂类的SQL会造成CPU的升高，进而会影响业务。

## 8 分库分表命名规则

#### 自增数字分表(库)，表(库)名使用自动补齐规则，如

1. User表分10张表，命名如下：User_0 ~ User_9
2. User表分100张表，命名如下：User_00 ~ User_99
3. User表分1000张表，命名如下:User_000 ~ User_999

#### 按年分表(库)，表(库)名后缀为对应的年份，如：

1. User_2017 ~ User_2020

####  按月分表(库)，表(库)名后缀为对应的年月，如：

1. User_201701 ~ User_202012

#### 按天分表(库)，表(库)名后缀为对应的年月日，如：

1. User_20170101 ~ User_20201201

## 9 常用字段数据类型范围

1. 数值类型

   1. | 数值类型              | 取值范围                                   |
      | --------------------- | ------------------------------------------ |
      | TINYINT(4)            | -128~127                                   |
      | TINYINT(4) UNSIGNED   | 0~255                                      |
      | SMALLINT(6)           | -32768~32767                               |
      | SMALLINT(6) UNSIGNED  | 0 ~ 65535                                  |
      | MEDIUMINT(8)          | -8388608 ~ 8388607                         |
      | MEDIUMINT(8) UNSIGNED | 0 ~ 16777215                               |
      | INT(11)               | -2147483648 ~ 2147483647                   |
      | INT(11) UNSIGNED      | 0 ~ 4294967295                             |
      | BIGINT(20)            | -9223372036854775808 ~ 9223372036854775807 |
      | BIGINT(20) UNSIGNED   | 0 ~ 18446744073709551615                   |

2. 字符类型

   1. VARCHAR(N)：在Mysql数据库中，VARCHAR(N)中的N代表N个字符，不管你是中文字符还是英文字符，VARCHAR(N)能存储最大为N个中文字符/英文字符

3. 时间类型

   1. TIMESTAMP：1970-01-01 00:00:01 UTC ~ 2038-01-19 03:14:07 UTC
   2. DATETIME: 1000-01-0100:00:00 ~ 9999-12-31 23:59:59



