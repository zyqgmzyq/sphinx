# 树

## [1.leetcode-104.二叉树的最大深度](https://leetcode-cn.com/problems/maximum-depth-of-binary-tree/)

### 题目描述

给定一个二叉树，找出其最大深度。二叉树的深度为根节点到最远叶子节点的最长路径上的节点数。说明: 叶子节点是指没有子节点的节点。给定二叉树 [3,9,20,null,null,15,7]，返回它的最大深度 3 。

### 递归方法

```c++
class Solution {
public:
    int maxDepth(TreeNode* root) {
        if(!root) return 0;
        int left=maxDepth(root->left);
        int right=maxDepth(root->right);
        return max(left, right)+1;
    }
};
```
### 非递归方法

```c++
class Solution {
    public:
    int maxDepth(TreeNode* root) {
        if(!root) return 0;
        int height=0;
        queue<TreeNode*> q;
        q.push(root);

        while(!q.empty()){
            int num_size = q.size();
            for(int i=0;i<num_size;i++){
                TreeNode *p = q.front();
                q.pop();
                if(p->left) q.push(p->left);
                if(p->right) q.push(p->right);
            }
            height++;
        }
        return height;
    }
};
```



## [2.leetcode-144.二叉树的前序遍历](https://leetcode-cn.com/problems/binary-tree-preorder-traversal/)

### 题目描述
给定一个二叉树，返回它的 前序 遍历。

### 非递归方法

```c++
class Solution {
public:
    vector<int> preorderTraversal(TreeNode* root) {
        if (!root) return {};
        vector<int> ret;

        stack<TreeNode*> s;
        while (root) {
            s.push(root);
            ret.push_back(root->val);
            root = root->left;
        }

        while (!s.empty()) {
            TreeNode *p = s.top();
            s.pop();

            if (p->right) {
                p = p->right;
                while (p) {
                    ret.push_back(p->val);
                    s.push(p);
                    p = p->left;
                }
            }
        }
        return ret;
    }
};
```



## [3.leetcode-94.二叉树的中序遍历](https://leetcode-cn.com/problems/binary-tree-inorder-traversal/)

### 题目描述
给定一个二叉树，返回它的 中序 遍历。

### 非递归方法

```c++
class Solution {
public:
    vector<int> inorderTraversal(TreeNode* root) {
        if (!root) return {};
        vector<int> ret;

        stack<TreeNode*> s;
        while (root) {
            s.push(root);
            root = root->left;
        }

        while (!s.empty()) {
            TreeNode *p = s.top();
            s.pop();
            ret.push_back(p->val);

            if (p->right) {
                p = p->right;
                while (p) {
                    s.push(p);
                    p = p->left;
                }
            }
        }
        return ret;
    }
};
```



## [4.leetcode-145.二叉树的后序遍历](https://leetcode-cn.com/problems/binary-tree-postorder-traversal/)

### 题目描述
给定一个二叉树，返回它的 后序 遍历。

### 非递归方法

```c++
class Solution {
public:
    vector<int> postorderTraversal(TreeNode* root) {
        if (!root) return {};
        vector<int> ret;
        stack<pair<TreeNode*, bool>> s;

        while (root) {
            s.push({ root, false});
            root = root->left;
        }

        while (!s.empty()) {
            auto p = s.top();
            s.pop();

            if (p.second) {
                ret.push_back(p.first->val);
                continue;
            }

            p.second = true;
            s.push(p);

            TreeNode *q = p.first;
            if (q->right) {
                q = q->right;
                while (q) {
                    s.push({ q, false });
                    q = q->left;
                }
            }
        }
        return ret;
    }
};
```