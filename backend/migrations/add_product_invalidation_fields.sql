-- 添加产品作废相关字段
-- 执行时间: 2025-12-27

USE agri_trace;

-- 添加作废相关字段
ALTER TABLE products
ADD COLUMN invalidated_at DATETIME NULL COMMENT '作废时间',
ADD COLUMN invalidated_by INT NULL COMMENT '作废操作人ID',
ADD COLUMN invalidated_reason TEXT NULL COMMENT '作废原因',
ADD CONSTRAINT fk_products_invalidated_by FOREIGN KEY (invalidated_by) REFERENCES users(id);

-- 添加索引
CREATE INDEX idx_products_invalidated_at ON products(invalidated_at);

-- 更新枚举类型（如果使用ENUM的话，否则跳过此步骤）
-- 注意：MySQL修改ENUM需要重新定义整个ENUM列
-- ALTER TABLE products MODIFY COLUMN status ENUM('draft', 'pending_chain', 'on_chain', 'terminated', 'invalidated') DEFAULT 'draft';

SELECT '数据库迁移完成：已添加产品作废相关字段' AS message;
