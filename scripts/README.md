# 区块链数据查询工具

这个目录包含用于查询 FISCO BCOS 链上数据的工具脚本。

## 工具列表

### 1. chain_explorer.py (推荐)

Python 版本的区块链浏览工具，提供格式化的数据展示。

**功能:**
- ✅ 查询产品详细信息（自动解析并格式化）
- ✅ 查询区块信息
- ✅ 查询交易详情
- ✅ 查看区块链高度
- ✅ 统计链上产品总数
- ✅ 自动转换数量单位（链上整数 ÷ 1000 = 实际数量）

**使用方法:**

```bash
# 查询产品信息
python3 scripts/chain_explorer.py product TRACE-20251226-D202763D

# 查询区块高度
python3 scripts/chain_explorer.py height

# 查询链上产品总数
python3 scripts/chain_explorer.py count

# 查询指定区块
python3 scripts/chain_explorer.py block 10

# 查询交易
python3 scripts/chain_explorer.py tx 0x7634ff391e44a3a69093d0e1c7bcba8f29ac850f6a71c27fcb91eadc2463f1d2
```

**输出示例:**

```
============================================================
产品查询: TRACE-20251226-0E87D447
============================================================

📦 产品信息:
  名称:      ??????
  类别:      ??????
  产地:      ?????????
  数量:      2.0 kg
  数量(原始): 2000 (链上存储的整数值)
  创建者:    0x4a13d56d21600a79cb5d32177e12779d603e6e00
  当前持有:  0x4a13d56d21600a79cb5d32177e12779d603e6e00
  创建时间:  2025-12-26 17:49:33
  记录数:    1
```

### 2. query_chain_data.sh

Bash 版本的查询脚本，直接调用 Console 命令。

**使用方法:**

```bash
# 查询产品
bash scripts/query_chain_data.sh product TRACE-20251226-D202763D

# 查询区块高度
bash scripts/query_chain_data.sh height

# 查询区块
bash scripts/query_chain_data.sh block 10

# 查询交易
bash scripts/query_chain_data.sh tx 0x1234...
```

## 当前链上数据统计

- **区块高度**: 12
- **产品总数**: 6
- **合约地址**: 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1

## 已知问题

### 中文字符显示为 ??????

这是 FISCO BCOS Console 输出编码的限制，链上实际存储的是正确的中文，但通过 Console 查询时会显示为问号。

**解决方案:**
- 数据是正确存储的，只是显示问题
- 可以通过查看 `数量(原始)` 字段来验证数据完整性
- 或者通过后端 API 查询数据库中的对应记录

### 芒果产品数据异常

产品 `TRACE-20251226-D202763D` (芒果) 的链上数量为 51242000，这是历史脏数据。

**对比:**
- 数据库中: 5.0 kg
- 应该上链的值: 5000 (5.0 * 1000)
- 实际链上值: 51242000 (错误)

**建议:** 删除该产品并重新创建测试数据。

## 数据格式说明

### 产品数据字段 (11个字段)

链上产品数据返回一个包含 11 个字段的元组:

```
(name, category, origin, quantity_int, unit, field5, field6, creator, current_holder, timestamp, record_count)
```

**字段说明:**
- `[0] name`: 产品名称
- `[1] category`: 产品类别
- `[2] origin`: 产地
- `[3] quantity_int`: 数量整数（实际数量 × 1000）
- `[4] unit`: 单位
- `[5-6]`: 预留字段
- `[7] creator`: 创建者地址
- `[8] current_holder`: 当前持有者地址
- `[9] timestamp`: 时间戳（毫秒）
- `[10] record_count`: 记录数量

### 数量存储规则

为了支持小数且避免浮点数精度问题，链上存储规则如下:

- **存储时**: `quantity_int = int(quantity * 1000)`
- **读取时**: `quantity = quantity_int / 1000`

**示例:**
- 实际数量: 2.5 kg
- 链上存储: 2500
- 读取显示: 2.5 kg

## 其他查询方式

### 直接使用 Console

```bash
cd /home/pdm/fisco/console

# 查询产品
bash console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProduct "TRACE-20251226-D202763D"

# 查询区块高度
bash console.sh getBlockNumber

# 查询区块
bash console.sh getBlockByNumber 10
```

### 通过后端 API

```bash
# 查询链上数据 (需要后端运行)
curl http://localhost:8000/api/blockchain/product/TRACE-20251226-D202763D/chain-data

# 查询区块链健康状态
curl http://localhost:8000/api/blockchain/health
```

## 开发参考

- **Console 路径**: `/home/pdm/fisco/console`
- **合约名称**: `AgriTrace`
- **合约地址**: `0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1`
- **RPC 地址**: `http://127.0.0.1:20200`
- **群组 ID**: `group0`
