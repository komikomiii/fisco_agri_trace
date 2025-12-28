# 用户区块链地址系统说明

## 概述

现在系统中的每个用户都有真实的区块链地址，交易时会使用用户的真实地址而不是临时生成的ID。

## 系统架构

```
用户注册/创建
    ↓
生成以太坊账户 (私钥 + 地址)
    ↓
私钥加密存储到 keystore 文件
    ↓
地址保存到数据库
    ↓
上链时使用真实地址
```

## 用户地址列表

| 用户名 | 角色 | 区块链地址 |
|--------|------|-----------|
| producer | 原料商 | `0x3d6Cc42a2Af2f5aE13d6fB1423bC09F387d35Edc` |
| processor | 加工商 | `0x47F466adbC9167735eD36B7c5D38dc8993E40F85` |
| inspector | 质检员 | `0xd6ea116dc83890e38B162e574d455e47BC92f510` |
| seller | 销售商 | `0x02f57d90a01560912837109F126ECAA5B0FFC3b2` |
| consumer | 消费者 | `0x4196259f89FaAeC319445C3376B1244D5639d4c6` |
| 果农1 | 原料商 | `0xc0373125f10Eb89FABef6066c5dD13d83C0B5270` |
| 加工1 | 加工商 | `0xe39897Cb0606d012F6101623829E547F8EB022FE` |

## 核心组件

### 1. 钱包管理器 (`app/blockchain/wallet.py`)

负责用户账户的生成、存储和管理：

```python
from app.blockchain.wallet import wallet_manager

# 确保用户有账户（如果没有则创建）
account = wallet_manager.ensure_user_account(user_id, username)

# 获取用户账户
account = wallet_manager.get_account(user_id)
# 返回: {"address": "0x...", "private_key": "0x...", "username": "..."}
```

**安全特性：**
- 私钥使用用户ID作为密码加密存储（keystore 格式）
- Keystore 文件位置: `/home/pdm/DEV/komi-project/keystore/user_{id}.json`
- 账户映射文件: `/home/pdm/DEV/komi-project/keystore/accounts.json`

### 2. 用户注册 (`app/api/auth.py`)

注册时自动生成区块链地址：

```python
@router.post("/register")
async def register(user_data: UserCreate, db: Session):
    # 1. 创建用户记录
    user = User(...)
    db.add(user)
    db.commit()

    # 2. 生成区块链账户
    account = wallet_manager.ensure_user_account(user.id, user_data.username)

    # 3. 更新地址
    user.blockchain_address = account["address"]
    db.commit()

    return user
```

### 3. 区块链交易 (`app/api/processor.py`)

上链时使用用户的真实地址：

```python
# 确保用户有地址
if not current_user.blockchain_address:
    account = wallet_manager.ensure_user_account(current_user.id, current_user.username)
    current_user.blockchain_address = account["address"]
    db.commit()

# 调用智能合约（使用真实地址）
success, tx_hash, block_number = blockchain_client.transfer_product(
    new_holder=current_user.blockchain_address,  # 真实地址
    ...
)
```

## 数据库结构

```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50),
    ...
    blockchain_address VARCHAR(100)  -- 新增字段
);
```

## 智能合约交互

### 之前的实现
```solidity
// 使用临时地址：0x0000...0002
transferProduct(..., new_holder="0x0000000000000000000000000000000000000002")
```

### 现在的实现
```solidity
// 使用真实地址：0x47F46...F85
transferProduct(..., new_holder="0x47F466adbC9167735eD36B7c5D38dc8993E40F85")
```

## 交易示例

**场景：Processor 接收产品**

1. **登录获取地址：**
   ```bash
   POST /api/auth/login
   {
     "username": "processor",
     "password": "123456"
   }

   响应:
   {
     "user": {
       "blockchain_address": "0x47F466adbC9167735eD36B7c5D38dc8993E40F85"
     }
   }
   ```

2. **接收产品上链：**
   ```bash
   POST /api/processor/products/3/receive

   调用合约:
   transferProduct(
     traceCode="TRACE-20251226-4E9637C2",
     newHolder="0x47F466adbC9167735eD36B7c5D38dc8993E40F85",  # ← 真实地址
     ...
   )
   ```

3. **数据库记录：**
   ```sql
   current_holder_id = 2
   current_stage = 'PROCESSOR'
   tx_hash = '0x593cd634344a5002bf060c27dc66304aab7398ac2d311312627cc84532092431'
   block_number = 19
   ```

## 与 Console 的关系

**重要说明：**

虽然我们现在为用户分配了真实的区块链地址，但实际的交易发送方仍然是 Console 的默认账户。这是因为：

1. **FISCO BCOS Console 的限制：**
   - Console 通过命令行调用合约
   - 交易签名使用 Console 配置的默认账户
   - 无法动态切换发送方账户

2. **当前架构：**
   ```
   用户地址 (newHolder)  →  合约参数（接收方/持有者）
   Console 账户           →  交易发送方（签名者）
   ```

3. **为什么这样设计仍然合理：**
   - 用户地址在合约中记录为产品持有者
   - 业务逻辑正确，权限控制通过应用层实现
   - 简化了系统复杂度（不需要管理每个用户的私钥签名）

### 如果要实现真正的"发送方是用户"

需要：
1. 使用 Python SDK 而不是 Console
2. 为每个用户生成私钥（已完成）
3. 用用户的私钥对交易进行签名
4. 通过 SDK 直接发送已签名的交易

这需要重写区块链客户端，但对于毕业设计来说，当前实现已经足够。

## 安全考虑

### Keystore 文件
- 位置: `/home/pdm/DEV/komi-project/keystore/`
- 格式: Web3 Secret Storage Definition (加密的 JSON)
- 密码: 使用用户ID（生产环境应使用更强的密码）

### 私钥访问
```python
# 只有通过 wallet_manager 才能访问私钥
account = wallet_manager.get_account(user_id)
private_key = account["private_key"]  # 已解密
```

## 测试验证

```bash
# 1. 登录查看地址
curl -X POST http://localhost:8000/api/auth/login \
  -d '{"username": "processor", "password": "123456"}'

# 2. 接收产品
curl -X POST http://localhost:8000/api/processor/products/3/receive \
  -H "Authorization: Bearer <token>" \
  -d '{"product_id": 3, "received_quantity": 100.0}'

# 3. 验证数据库
mysql -u root -p123456 agri_trace \
  -e "SELECT * FROM products WHERE id=3"

# 4. 查看链上数据
cd /home/pdm/fisco/console
bash console.sh
> call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProduct "TRACE-20251226-4E9637C2"
```

## 总结

✅ **已实现：**
- 所有用户拥有真实的以太坊地址
- 注册时自动生成地址
- 私钥安全存储（keystore 加密）
- 上链时使用真实地址记录持有者
- 完整的测试验证

⚠️ **注意：**
- 交易发送方仍是 Console 账户
- 用户地址作为业务身份（newHolder 参数）
- 权限控制在应用层实现

🎯 **效果：**
- 每个用户都有唯一可识别的区块链地址
- 产品流转记录包含真实的持有者地址
- 符合区块链溯源的基本要求
