# 排序算法

## 1. 冒泡排序

冒泡排序重复地走访过要排序的元素列，依次比较两个相邻的元素，如果他们的顺序（如从大到小、首字母从A到Z）错误就把他们交换过来。走访元素的工作是重复地进行直到没有相邻元素需要交换，也就是说该元素已经排序完成。

### 解题步骤

1.比较相邻的元素。如果第一个比第二个大，就交换它们两个；
2.针对所有的元素重复以上的步骤，除了最后一个；

### 复杂度和稳定性

- 平均时间复杂度：O(n^2)
- 最坏时间复杂度：O(n^2)
- 最好时间复杂度：O(n)
- 空间复杂度：O(1)
- 稳定性：稳定排序

### 代码

```c++
void bubbleSort(vector<int> &nums){
    for(int i=0;i<nums.size()-1;i++){
        for(int j=0;j<nums.size()-i-1;j++){
            if(nums[j]>nums[j+1]){
                int temp = nums[j];
                nums[j] = nums[j+1];
                nums[j+1] = temp;
            }
        }
    }
}
```



## 2.选择排序

选择排序（Selection sort）是一种简单直观的[排序算法](https://baike.baidu.com/item/%E6%8E%92%E5%BA%8F%E7%AE%97%E6%B3%95/5399605)。它的工作原理是每一次从待排序的[数据元素](https://baike.baidu.com/item/%E6%95%B0%E6%8D%AE%E5%85%83%E7%B4%A0/715313)中选出最小（或最大）的一个元素，存放在序列的起始位置，然后，再从剩余未排序元素中继续寻找最小（大）元素，然后放到已排序序列的末尾。以此类推，直到全部待排序的数据元素排完。 选择排序是不稳定的排序方法。

### 解题步骤

1.假设排序表为 L[1....n] 
2.第i趟排序即从 L[i,,,,n]  中选择关键字最小的元素与 L(i) 交换，每一趟排序可以确定一个元素的最终位置，这样经过 n-1 趟排序就可以使整个排序表有序。

### 复杂度和稳定性

- 平均时间复杂度：O(n^2)
- 最坏时间复杂度：O(n^2)
- 最好时间复杂度：O(n^2)
- 空间复杂度：O(1)
- 稳定性：不稳定排序

### 代码

```c++
void selectSort(vector<int> &nums){
    for(int i=0;i<nums.size()-1;i++){
        int temp=i;
        for(int j=i+1;j<nums.size();j++){
            if(nums[j]<nums[temp]) temp = j;
        }
        swap(nums[temp], nums[i]);
    }
}
```



## 3.插入排序
插入排序的基本操作就是将一个数据插入到已经排好序的有序数据中，从而得到一个新的、个数加一的有序数据，算法适用于少量数据的排序。

### 解题步骤

1.从第一个元素开始，该元素可以认为已经被排序；
2.取出下一个元素，在已经排序的元素序列中从后向前扫描直到从已排序序列中找到比新元素小或者等的元素（t）；
3.将新元素插入在这个元素（t）后面。

### 复杂度和稳定性

- 平均时间复杂度：O(n^2)
- 最坏时间复杂度：O(n^2)
- 最好时间复杂度：O(n)
- 空间复杂度：O(1)

- 稳定性：稳定排序

### 代码

```c++
void insertSort(vector<int> &nums){
    for(int j=1; j<nums.size(); j++){
        int temp = nums[j];
        int i = j-1;
        while(i>=0 && nums[i]>temp){
            nums[i+1] = nums[i];
            i--;
        }
        nums[i+1] = temp;
    }
}
```



## 4.归并排序

归并排序（MERGE-SORT）是建立在归并操作上的一种有效的排序算法,该算法是采用分治法（Divide and Conquer）的一个非常典型的应用。将已有序的子序列合并，得到完全有序的序列；即先使每个子序列有序，再使子序列段间有序。若将两个有序表合并成一个有序表，称为二路[归并](https://baike.baidu.com/item/%E5%BD%92%E5%B9%B6/253741)。

### 解题步骤

1.把输入序列分成子序列；
2.对这两个子序列分别采用归并排序；
3.将两个排序好的子序列合并成一个最终的排序序列。

### 复杂度和稳定性

- 平均时间复杂度：O(nlogn)
- 最坏时间复杂度：O(nlogn)
- 最好时间复杂度：O(nlogn)
- 空间复杂度：O(n)
- 稳定性：稳定排序

### 代码


```c++
void _merge(vector<int> &nums, int left, int med, int right){
    vector<int> L(nums.begin()+left, nums.begin()+med+1);
    vector<int> R(nums.begin()+med+1, nums.begin()+right+1);
    // 设置哨兵  简化代码  不用每次判断数组是否为空
    L.push_back(INT_MAX);
    R.push_back(INT_MAX);
    int i=0, j=0;

    for(int k=left; k<=right; k++){
        if(L[i] < R[j]){
            nums[k] = L[i];
            i++;
        }else{
            nums[k] = R[j];
            j++;
        }
    }
}

void _sort(vector<int> &nums, int left, int right){
    int med = (left+right)/2;
    if(left < right){
        _sort(nums, left, med);
        _sort(nums, med+1, right);
        _merge(nums, left, med, right);
    }
}

void mergeSort(vector<int> &nums){
    _sort(nums, 0, nums.size()-1);
}
```



## 5.快速排序

快速排序（Quicksort）是对[冒泡排序](https://baike.baidu.com/item/%E5%86%92%E6%B3%A1%E6%8E%92%E5%BA%8F/4602306)的一种改进。它的基本思想是：通过一趟排序将要排序的数据分割成独立的两部分，其中一部分的所有数据都比另外一部分的所有数据都要小，然后再按此方法对这两部分数据分别进行快速排序，整个排序过程可以[递归](https://baike.baidu.com/item/%E9%80%92%E5%BD%92/1740695)进行，以此达到整个数据变成有序[序列](https://baike.baidu.com/item/%E5%BA%8F%E5%88%97/1302588)。

### 解题步骤

1.选取最后一个元素值作为基准值，使得左边的数比当前值小，右边的数比当前值大；
2.创建两个数组下标，一个为 cur记录当前数字，一个为pre记录cur的前一个数字；
3.如果cur的数字大于基准值，pre不动，cur++；如果cur的数字小于基准值则交换cur和pre的数字，cur++,pre++；
4.交换基准值和pre的数字。

### 复杂度和稳定性

- 平均时间复杂度：O(nlogn)
- 最坏时间复杂度：O(n^2)
- 最好时间复杂度：O(nlogn)
- 空间复杂度：O(nlogn)

- 稳定性：不稳定排序

### 递归实现

```c++
int partition_(vector<int>& nums, int p, int r){
    int base = nums[r];
    int pre=p;
    for(int cur=pre;cur<r;cur++){
        if(nums[cur]<=base){
            swap(nums[pre], nums[cur]);
            pre++;
        }
    }
    swap(nums[pre], nums[r]);
    return pre;
}

void quickSort(vector<int>& nums, int p, int r){
    if(p<r){
        int q = partition_(nums, p, r);
        quickSort(nums, p, q-1);
        quickSort(nums, q+1, r);
    }
}
```

### 非递归实现    

```c++
int partition_(vector<int>& nums, int p, int r){
    int base = nums[r];
    int pre=p;
    for(int cur=pre;cur<r;cur++){
        if(nums[cur]<=base){
            if(pre!=cur) swap(nums[pre], nums[cur]);
            pre++;
        }
    }
    swap(nums[pre], nums[r]);
    return pre;
}

void quickSort_(vector<int>& nums, int p, int r){
    stack<int> s;
    s.push(p);
    s.push(r);
    int left,right;

    while(!s.empty()){
        right = s.top();
        s.pop();
        left = s.top();
        s.pop();

        if(left<right){
            int q = partition_(nums, left, right);
            s.push(left);
            s.push(q-1);
            s.push(q+1);
            s.push(right);
        }
    }
}
```



## 6.堆排序

堆排序是利用堆这种数据结构而设计的一种排序算法，堆排序是一种选择排序。

### 解题步骤

[参考 ](https://www.cnblogs.com/chengxiao/p/6129630.html)https://www.cnblogs.com/chengxiao/p/6129630.html

1. 将无序序列构建成一个堆，根据升序降序需求选择大顶堆或小顶堆;
2. 将堆顶元素与末尾元素交换，将最大元素"沉"到数组末端;
3. 重新调整结构，使其满足堆定义，然后继续交换堆顶元素与当前末尾元素，反复执行调整+交换步骤，直到整个序列有序。

### 复杂度和稳定性

- 平均时间复杂度：O(nlogn)
- 最坏时间复杂度：O(nlogn)
- 最好时间复杂度：O(nlogn)
- 空间复杂度：O(1)

- 稳定性：不稳定排序

### 代码


```c++
void maxHeap(vector<int> &nums, int i, int high){
    int left = 2*i+1, right = 2*i+2;
    int largest;
    if(left<high && nums[left]>nums[i]) largest = left;
    else largest = i;
    if(right<high&&nums[right]>nums[largest]) largest = right;

    if(largest!=i){
        swap(nums[i], nums[largest]);
        maxHeap(nums, largest, high);
    }
}

void bulidHeap(vector<int> &nums){
    for(int i=nums.size()/2-1; i>=0; i--){
        maxHeap(nums, i, nums.size());
    }
}

void heapSort(vector<int> &nums){
    bulidHeap(nums);
    for(int i=nums.size()-1; i>0; i--){
        swap(nums[0], nums[i]);
        maxHeap(nums, 0, i);
    }
}

int main()
{
    vector<int> nums = {16, 4, 10, 14, 7, 9, 3, 2, 8, 1};
    heapSort(nums);
    for(auto num:nums){
        cout << num << " ";
    }
    cout << endl;
    return 0;
}
```

