// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title AgriTrace - 农产品溯源智能合约
 * @dev 基于 FISCO BCOS 的农产品全程溯源系统
 */
contract AgriTrace {

    // ==================== 枚举定义 ====================

    // 产品阶段
    enum Stage {
        PRODUCER,   // 原料阶段
        PROCESSOR,  // 加工阶段
        INSPECTOR,  // 质检阶段
        SELLER,     // 销售阶段
        SOLD        // 已售出
    }

    // 产品状态
    enum Status {
        ON_CHAIN,    // 已上链
        TERMINATED   // 已终止
    }

    // 操作类型
    enum Action {
        CREATE,         // 创建
        HARVEST,        // 采收上链
        RECEIVE,        // 接收
        PROCESS,        // 加工
        SEND_INSPECT,   // 送检
        INSPECT,        // 质检
        REJECT,         // 退回
        TERMINATE,      // 终止
        STOCK_IN,       // 入库
        SELL,           // 销售
        AMEND           // 修正
    }

    // ==================== 数据结构 ====================

    // 产品主信息
    struct Product {
        string traceCode;       // 溯源码 (唯一标识)
        string name;            // 产品名称
        string category;        // 品类
        string origin;          // 产地
        uint256 quantity;       // 数量 (乘以1000存储，支持3位小数)
        string unit;            // 单位
        Stage currentStage;     // 当前阶段
        Status status;          // 状态
        address creator;        // 创建者地址
        address currentHolder;  // 当前持有者
        uint256 createdAt;      // 创建时间
        uint256 recordCount;    // 记录数量
    }

    // 流转记录
    struct Record {
        uint256 recordId;       // 记录ID
        string traceCode;       // 溯源码
        Stage stage;            // 操作阶段
        Action action;          // 操作类型
        string data;            // 操作数据 (JSON格式)
        string remark;          // 备注
        address operator;       // 操作人地址
        string operatorName;    // 操作人名称
        uint256 timestamp;      // 时间戳
        uint256 previousRecordId; // 前一条记录ID (修正时使用)
        string amendReason;     // 修正原因
    }

    // ==================== 状态变量 ====================

    // 溯源码 => 产品信息
    mapping(string => Product) public products;

    // 溯源码 => 记录列表
    mapping(string => Record[]) public productRecords;

    // 已存在的溯源码
    mapping(string => bool) public traceCodeExists;

    // 产品总数
    uint256 public productCount;

    // 记录总数
    uint256 public recordCount;

    // 管理员
    address public admin;

    // ==================== 事件 ====================

    event ProductCreated(
        string indexed traceCode,
        string name,
        address creator,
        uint256 timestamp
    );

    event RecordAdded(
        string indexed traceCode,
        uint256 recordId,
        Stage stage,
        Action action,
        address operator,
        uint256 timestamp
    );

    event ProductTransferred(
        string indexed traceCode,
        address from,
        address to,
        Stage newStage,
        uint256 timestamp
    );

    event ProductTerminated(
        string indexed traceCode,
        string reason,
        address operator,
        uint256 timestamp
    );

    // ==================== 修饰器 ====================

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }

    modifier productExists(string memory _traceCode) {
        require(traceCodeExists[_traceCode], "Product does not exist");
        _;
    }

    modifier notTerminated(string memory _traceCode) {
        require(products[_traceCode].status != Status.TERMINATED, "Product is terminated");
        _;
    }

    // ==================== 构造函数 ====================

    constructor() {
        admin = msg.sender;
    }

    // ==================== 产品管理 ====================

    /**
     * @dev 创建产品 (原料商上链)
     */
    function createProduct(
        string memory _traceCode,
        string memory _name,
        string memory _category,
        string memory _origin,
        uint256 _quantity,
        string memory _unit,
        string memory _data,
        string memory _operatorName
    ) public returns (bool) {
        require(!traceCodeExists[_traceCode], "Trace code already exists");
        require(bytes(_traceCode).length > 0, "Trace code cannot be empty");
        require(bytes(_name).length > 0, "Name cannot be empty");

        // 创建产品
        Product storage product = products[_traceCode];
        product.traceCode = _traceCode;
        product.name = _name;
        product.category = _category;
        product.origin = _origin;
        product.quantity = _quantity;
        product.unit = _unit;
        product.currentStage = Stage.PRODUCER;
        product.status = Status.ON_CHAIN;
        product.creator = msg.sender;
        product.currentHolder = msg.sender;
        product.createdAt = block.timestamp;
        product.recordCount = 0;

        traceCodeExists[_traceCode] = true;
        productCount++;

        // 添加创建记录
        _addRecord(
            _traceCode,
            Stage.PRODUCER,
            Action.HARVEST,
            _data,
            "",
            _operatorName,
            0,
            ""
        );

        emit ProductCreated(_traceCode, _name, msg.sender, block.timestamp);

        return true;
    }

    /**
     * @dev 添加流转记录
     */
    function addRecord(
        string memory _traceCode,
        Stage _stage,
        Action _action,
        string memory _data,
        string memory _remark,
        string memory _operatorName
    ) public productExists(_traceCode) notTerminated(_traceCode) returns (uint256) {
        return _addRecord(_traceCode, _stage, _action, _data, _remark, _operatorName, 0, "");
    }

    /**
     * @dev 添加修正记录
     */
    function addAmendRecord(
        string memory _traceCode,
        Stage _stage,
        string memory _data,
        string memory _remark,
        string memory _operatorName,
        uint256 _previousRecordId,
        string memory _amendReason
    ) public productExists(_traceCode) notTerminated(_traceCode) returns (uint256) {
        require(bytes(_amendReason).length > 0, "Amend reason is required");
        return _addRecord(_traceCode, _stage, Action.AMEND, _data, _remark, _operatorName, _previousRecordId, _amendReason);
    }

    /**
     * @dev 内部添加记录函数
     */
    function _addRecord(
        string memory _traceCode,
        Stage _stage,
        Action _action,
        string memory _data,
        string memory _remark,
        string memory _operatorName,
        uint256 _previousRecordId,
        string memory _amendReason
    ) internal returns (uint256) {
        recordCount++;
        uint256 newRecordId = recordCount;

        Record memory newRecord = Record({
            recordId: newRecordId,
            traceCode: _traceCode,
            stage: _stage,
            action: _action,
            data: _data,
            remark: _remark,
            operator: msg.sender,
            operatorName: _operatorName,
            timestamp: block.timestamp,
            previousRecordId: _previousRecordId,
            amendReason: _amendReason
        });

        productRecords[_traceCode].push(newRecord);
        products[_traceCode].recordCount++;

        emit RecordAdded(_traceCode, newRecordId, _stage, _action, msg.sender, block.timestamp);

        return newRecordId;
    }

    /**
     * @dev 转移产品到下一阶段
     */
    function transferProduct(
        string memory _traceCode,
        address _newHolder,
        Stage _newStage,
        string memory _data,
        string memory _remark,
        string memory _operatorName
    ) public productExists(_traceCode) notTerminated(_traceCode) returns (bool) {
        Product storage product = products[_traceCode];

        // 确定操作类型
        Action action;
        if (_newStage == Stage.PROCESSOR) {
            action = Action.RECEIVE;
        } else if (_newStage == Stage.INSPECTOR) {
            action = Action.SEND_INSPECT;
        } else if (_newStage == Stage.SELLER) {
            action = Action.STOCK_IN;
        } else if (_newStage == Stage.SOLD) {
            action = Action.SELL;
        } else {
            action = Action.RECEIVE;
        }

        address previousHolder = product.currentHolder;
        product.currentHolder = _newHolder;
        product.currentStage = _newStage;

        // 添加转移记录
        _addRecord(_traceCode, _newStage, action, _data, _remark, _operatorName, 0, "");

        emit ProductTransferred(_traceCode, previousHolder, _newHolder, _newStage, block.timestamp);

        return true;
    }

    /**
     * @dev 质检通过
     */
    function inspectPass(
        string memory _traceCode,
        string memory _data,
        string memory _remark,
        string memory _operatorName
    ) public productExists(_traceCode) notTerminated(_traceCode) returns (bool) {
        _addRecord(_traceCode, Stage.INSPECTOR, Action.INSPECT, _data, _remark, _operatorName, 0, "");
        return true;
    }

    /**
     * @dev 退回产品
     */
    function rejectProduct(
        string memory _traceCode,
        Stage _rejectToStage,
        address _rejectToHolder,
        string memory _data,
        string memory _reason,
        string memory _operatorName
    ) public productExists(_traceCode) notTerminated(_traceCode) returns (bool) {
        Product storage product = products[_traceCode];

        address previousHolder = product.currentHolder;
        product.currentHolder = _rejectToHolder;
        product.currentStage = _rejectToStage;

        // 添加退回记录
        _addRecord(_traceCode, Stage.INSPECTOR, Action.REJECT, _data, _reason, _operatorName, 0, "");

        emit ProductTransferred(_traceCode, previousHolder, _rejectToHolder, _rejectToStage, block.timestamp);

        return true;
    }

    /**
     * @dev 终止产品链
     */
    function terminateProduct(
        string memory _traceCode,
        string memory _data,
        string memory _reason,
        string memory _operatorName
    ) public productExists(_traceCode) notTerminated(_traceCode) returns (bool) {
        Product storage product = products[_traceCode];
        product.status = Status.TERMINATED;

        // 添加终止记录
        _addRecord(_traceCode, product.currentStage, Action.TERMINATE, _data, _reason, _operatorName, 0, "");

        emit ProductTerminated(_traceCode, _reason, msg.sender, block.timestamp);

        return true;
    }

    // ==================== 查询函数 ====================

    /**
     * @dev 获取产品信息
     */
    function getProduct(string memory _traceCode) public view productExists(_traceCode) returns (
        string memory name,
        string memory category,
        string memory origin,
        uint256 quantity,
        string memory unit,
        Stage currentStage,
        Status status,
        address creator,
        address currentHolder,
        uint256 createdAt,
        uint256 recordCountNum
    ) {
        Product storage product = products[_traceCode];
        return (
            product.name,
            product.category,
            product.origin,
            product.quantity,
            product.unit,
            product.currentStage,
            product.status,
            product.creator,
            product.currentHolder,
            product.createdAt,
            product.recordCount
        );
    }

    /**
     * @dev 获取产品记录数量
     */
    function getRecordCount(string memory _traceCode) public view productExists(_traceCode) returns (uint256) {
        return productRecords[_traceCode].length;
    }

    /**
     * @dev 获取指定索引的记录
     */
    function getRecord(string memory _traceCode, uint256 _index) public view productExists(_traceCode) returns (
        uint256 recordId,
        Stage stage,
        Action action,
        string memory data,
        string memory remark,
        address operator,
        string memory operatorName,
        uint256 timestamp,
        uint256 previousRecordId,
        string memory amendReason
    ) {
        require(_index < productRecords[_traceCode].length, "Index out of bounds");
        Record storage record = productRecords[_traceCode][_index];
        return (
            record.recordId,
            record.stage,
            record.action,
            record.data,
            record.remark,
            record.operator,
            record.operatorName,
            record.timestamp,
            record.previousRecordId,
            record.amendReason
        );
    }

    /**
     * @dev 验证溯源码是否存在
     */
    function verifyTraceCode(string memory _traceCode) public view returns (bool) {
        return traceCodeExists[_traceCode];
    }

    /**
     * @dev 获取产品总数
     */
    function getProductCount() public view returns (uint256) {
        return productCount;
    }

    /**
     * @dev 获取记录总数
     */
    function getTotalRecordCount() public view returns (uint256) {
        return recordCount;
    }
}
