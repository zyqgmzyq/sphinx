# vsock

## 相关配置

**HOST: CONFIG_VHOST_VSOCK**

```shell
modprobe vmw_vsock_virtio_transport_common.ko
cd /lib/modules/`uname -r`/kernel/drivers/vhost
insmod vhost.ko
insmod vhost_vsock.ko
```

**GUEST:CONFIG_VIRTIO_VSOCKETS**

```shell
CONFIG_VSOCKETS=y
CONFIG_VIRTIO_VSOCKETS=y
```

QEMU虚拟机启动时需配置vsock 设备，配置参数为" -device vhost-vsock-pci,guest-cid=3"；

guest-cid必须大于等于3，2为HOST的ID。



## SOCKET编程

【socket编程概述】https://blog.csdn.net/yangkunqiankun/article/details/75808401

【send与recv 缓冲区与阻塞】https://blog.csdn.net/yangkunqiankun/article/details/75943596

【vsock详解】https://www.venustech.com.cn/new_type/aqldfx/20210310/22463.html



## MindSpore编译安装

```shell
git clone -b master https://github.com/mindspore-ai/mindspore.git

# 加-i选项可以增量编译。
bash build.sh  -I x86_64

# 执行推理过程
cd mindspore/lite/examples/quick_start_cpp/
bash build.sh
cd build
./mindspore_quick_start_cpp ../model/mobilenetv2.ms
```



## Guest发送

```c++
/* 防止send不完整 */
bool SendAll(int s, char *buffer, int size) {
  while (size>0) {
	  int sendSz= send(s, buffer, size, 0);
	  if(-1 == sendSz) {
	    return false;
	  }
	  size = size - sendSz;
	  buffer += sendSz;
	  printf("%d ", size);
  }
  return true;
}

namespace mindspore {
int LoadGuestModel(const void *model_data, size_t data_size) {
    int s = socket(AF_VSOCK, SOCK_STREAM, 0);
    struct sockaddr_vm addr;

    memset(&addr, 0, sizeof(struct sockaddr_vm));
    addr.svm_family = AF_VSOCK;
    addr.svm_port = 9999;
    addr.svm_cid = VMADDR_CID_HOST;
    connect(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));

    uint64_t prefix_size = 2 * sizeof(uint32_t) + sizeof(uint64_t);
    char *data = (char *)malloc(prefix_size);
    uint32_t type = 1;
    uint32_t id = 1;
    int64_t size = data_size;
    memcpy(data, &type, sizeof(uint32_t));
    memcpy(data + sizeof(uint32_t), &id, sizeof(uint32_t));
    memcpy(data + 2 * sizeof(uint32_t), &size, sizeof(uint64_t));
    send(s, data, prefix_size, 0);

    char *data1 = (char *)malloc(data_size);
    memcpy(data1, model_data, data_size);

    bool ret = SendAll(s, data1, data_size);
    printf("send ret = %d\n", ret);

    char buf[2];
    recv(s, &buf, 2, 0);
    printf("recv ret %s\n", buf);

    close(s);
    return 0;
}
} // namespace mindspore
```



## Host接收

```c++
#include <algorithm>
#include <random>
#include <iostream>
#include <fstream>
#include <cstring>
#include <sys/socket.h>
#include <linux/vm_sockets.h>
#include <include/api/serialization.h>
#include <include/api/context.h>
#include <include/api/model.h>
#include <include/api/cell.h>
#include <include/api/types.h>

auto context = std::make_shared<mindspore::Context>();
auto cpu_context = std::make_shared<mindspore::CPUDeviceInfo>();
mindspore::Graph graph;

int s = socket(AF_VSOCK, SOCK_STREAM, 0);
struct sockaddr_vm addr;

template <typename T, typename Distribution>
void GenerateRandomData(int size, void *data, Distribution distribution) {
	std::mt19937 random_engine;
	int elements_num = size / sizeof(T);
	(void)std::generate_n(static_cast<T *>(data), elements_num,
                        [&distribution, &random_engine]() { return static_cast<T>(distribution(random_engine)); });
}

int GenerateInputDataWithRandom(std::vector<mindspore::MSTensor> inputs) {
  for (auto tensor : inputs) {
    auto input_data = tensor.MutableData();
    if (input_data == nullptr) {
    	std::cerr << "MallocData for inTensor failed." << std::endl;
    	return -1;
    }
    GenerateRandomData<float>(tensor.DataSize(), input_data, std::uniform_real_distribution<float>(0.1f, 1.0f));
  }
  return 0;
}

static void handle_load(char *data, uint64_t size) {
	mindspore::Status ret = mindspore::Serialization::Load(data, size, mindspore::ModelType::kMindIR, &graph);
	if (ret != mindspore::kSuccess) {
		std::cerr << "Load model failed." << std::endl;
	}
	std::cout << "Load success\n" << std::endl;		// create graph cell
	mindspore::GraphCell cell(graph);
	// compile graph
	mindspore::Model model;
	ret = model.Build(cell, context);
	if (ret != mindspore::kSuccess) {
		std::cerr << "Build model failed." << std::endl;		return;
	}
	// input
	std::vector<mindspore::MSTensor> inputs = model.GetInputs();
	auto res = GenerateInputDataWithRandom(inputs);
	if (res != mindspore::kSuccess) {
		std::cerr << "Generate Random Input Data failed." << std::endl;
		return;
	}
	// init outputs
	std::vector<mindspore::MSTensor> outputs;
	// run
	model.Predict(inputs, &outputs);
	// get outputs
	std::vector<mindspore::MSTensor> output_tensors = model.GetOutputs();
	for (auto tensor : output_tensors) {
		auto out_data = reinterpret_cast<float *>(tensor.MutableData());
		std::cout << "output data is:";
		for (int i = 0; i < tensor.ElementNum() && i <= 50; i++) {
			std::cout << out_data[i] << " ";
		}
		std::cout << std::endl;
	}
}

/* 防止recv不完整 */
bool RecvAll(int peer_fd, char* buffer, int size)
{
	while (size>0)
	{
		int RecvSize= recv(peer_fd, buffer, size, 0);
		if(-1==RecvSize)
			return false;
		size = size - RecvSize;
		buffer+=RecvSize;
	}
	return true;
}

uint32_t recv_data(int peer_fd) {
	uint32_t type;
	uint32_t id;
	uint64_t size;
	size_t msg_len;

	uint32_t prefix_size = 2 * sizeof(uint32_t) + sizeof(uint64_t);
	char buf[prefix_size];

	msg_len = recv(peer_fd, &buf, prefix_size, 0);
	if (msg_len < 0) {
    	return -1;
	}
	memcpy(&type, buf, sizeof(uint32_t));
	memcpy(&id, buf + sizeof(uint32_t), sizeof(uint32_t));
	memcpy(&size, buf + 2 * sizeof(uint32_t), sizeof(uint64_t));

	printf("type:%d\n ", type);
	printf("id:%d\n ", id);
	printf("size:%d\n ", size);

	char *data = (char *)malloc(size);
	RecvAll(peer_fd, data, size);

	printf("receive end\n");

	if (type == 1) {
    	handle_load(data, size);
	}
	return -1;
}

int main(int argc, const char **argv) {
	context->SetThreadNum(3);
	cpu_context->SetEnableFP16(true);
	context->MutableDeviceInfo().push_back(cpu_context);

	memset(&addr, 0, sizeof(struct sockaddr_vm));
	addr.svm_family = AF_VSOCK;
	addr.svm_port = 9999;
	addr.svm_cid = VMADDR_CID_HOST;

	bind(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_vm));
	listen(s, 0);
	struct sockaddr_vm peer_addr;
	socklen_t peer_addr_size = sizeof(struct sockaddr_vm);
	int peer_fd = accept(s, (struct sockaddr *)&peer_addr, &peer_addr_size);

	printf("begin recv data:\n");
	recv_data(peer_fd);
    
    /* send ok to notify correct recv the data */
    int sentSize = send(peer_fd, "OK", 2, 0);
	printf("send ok end %d \n", sentSize);
}
```

