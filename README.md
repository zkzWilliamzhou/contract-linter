# contract-linter

**C++26 Contracts-aware static analysis for development-time safety verification - catch precondition/postcondition violations before runtime**

[![C++26](https://img.shields.io/badge/C%2B%2B26-active-green)](https://isocpp.org/std/status)
[![Stars](https://img.shields.io/github/stars/zkzWilliamzhou/contract-linter?style=social)](https://github.com/zkzWilliamzhou/contract-linter)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## 🎯 Why This Exists

C++26的契约(C++ Contracts)是革命性的，但目前缺少：
- 静态分析工具验证契约一致性
- CI集成检测潜在违规
- 契约复杂度可视化

**contract-linter 填补这一空白。**

## ✨ Key Features

- **契约一致性检查**：检测前置/后置条件冲突
- **CI/CD原生集成**：在CI管道中运行
- **契约复杂度分析**：可视化契约复杂度热力图
- **违规模式检测**：识别潜在契约违规代码

## 🔧 使用示例

```cpp
// 输入代码
int transfer(Account& from, Account& to, int amount) 
    pre(amount > 0) 
    pre(from.balance >= amount) 
    post(from.balance >= 0) 
{
    from.balance -= amount;
    to.balance += amount;
}
```

运行分析：
```bash
# 分析单个文件
contract-linter transfer.cpp

# CI模式（遇到警告/错误退出非零）
contract-linter --ci-mode *.cpp

# JSON输出
contract-linter --format json src/
```

## 📊 契约分析

| 检查类型 | 描述 |
|----------|------|
| 前置条件 | 函数调用者保证 |
| 后置条件 | 函数实现者保证 |
| 不变式 | 类不变式 |
| 复杂度 | 契约嵌套深度 |

## 🛠️ 安装

```bash
# 通过pip安装
pip install contract-linter

# 或从源码构建
git clone https://github.com/zkzWilliamzhou/contract-linter.git
cd contract-linter
python -m venv venv && source venv/bin/activate
pip install -e .
```

## 💻 集成使用

### GitHub Actions
```yaml
- name: Install Contract Linter
  run: pip install contract-linter

- name: Run Contract Linter
  run: contract-linter --ci-mode src/*.cpp
```

### Git Hook
```bash
# pre-commit hook
contract-linter --ci-mode src/
```

## 🤝 合作生态

与以下工具集成：
- clang-tidy
- cppcheck
- AddressSanitizer
- GitHub CodeQL

## 📄 许可证

MIT License